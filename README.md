# stock-researcher

A stock research and rating engine for US-listed common stocks, built like a small research firm. A
deterministic Python core pulls market data, normalizes it into a typed snapshot, grades it on an 18-metric
weighted scorecard, derives an earnings-based fair value and entry price, and suggests a label (BUY, WAIT,
HAS RUN, SELL, NOT LOOKING) by eight documented rules. On top of that, a Claude Code
`/research <TICKER>` command fans out to five specialist research agents and lets a planner write the final
verdict.

The design goal is a rating that is both reproducible and defensible: every number in a report comes from
code with tests, every threshold is written down in `docs/` (and a test fails if the docs drift from the
code), and the one place judgment enters — the planner confirming or overriding the suggested label — is
recorded next to the mechanical label in a ledger, so overrides are auditable after the fact.

## Architecture

```
market data (yfinance, behind a provider Protocol)
  -> snapshot      data/<T>.json          normalized fields, fractions and multiples only
  -> scorecard     data/<T>.score.json    18 metrics, A-F bands, weighted 0-100 + coverage
  -> fair value    forward EPS x median historical P/E, band, margin of safety, entry price
  -> label         rules L1-L8, first match wins           (all of the above: `run`)
  -> skeleton      data/<T>/skeleton.md
  -> agents        data/<T>/<agent>.md    valuation, growth-quality, balance-sheet-risk, technicals, news-catalysts
  -> verdict       data/<T>/verdict.md    the planner: final label, thesis, risks, triggers
  -> report        reports/<T>-<date>.md  front-matter + filled skeleton          (`assemble`)
  -> ledger        reports/ratings.csv    rebuilt from every report's front-matter (`ledger`)
```

## How to run

```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m stock_researcher snapshot AAPL   # data/AAPL.json
.venv/Scripts/python.exe -m stock_researcher score AAPL      # data/AAPL.score.json + one-line summary
.venv/Scripts/python.exe -m stock_researcher run AAPL        # snapshot + score + data/AAPL/skeleton.md
.venv/Scripts/python.exe -m stock_researcher assemble AAPL   # needs data/AAPL/verdict.md; writes reports/AAPL-<date>.md
.venv/Scripts/python.exe -m stock_researcher ledger          # rebuilds reports/ratings.csv
.venv/Scripts/python.exe -m pytest -q                        # offline test suite (no network)
```

## How the scorecard works

Five categories — valuation 30, growth 20, profitability 20, health 20, momentum 10 — each made of metrics
graded A-F on absolute bands; missing metrics drop out and the rest renormalize, and coverage below 60% means
the score is not trusted. The full band table and the special cases are in
[docs/scorecard.md](docs/scorecard.md); the fair-value method and its limits in
[docs/fair-value.md](docs/fair-value.md); the label rules and the override protocol in
[docs/labels.md](docs/labels.md).

## Research agents

Each agent reads only the snapshot and score files and may cite only numbers present there (with
the key in parentheses), so the agents interpret rather than compute. Each writes one markdown file into a
fixed slot of the report skeleton, keeping the planner's context small: it reads the scores and short agent
summaries and writes a ~150-word verdict. `assemble` stitches everything together mechanically, and the
ledger keeps both the rule-suggested and the final label.

## Research flow

Open Claude Code in the repo root and run `/research <TICKER>` (`.claude/commands/research.md`). It runs
`run` for the snapshot, score and skeleton, then dispatches five Opus analysts in parallel (valuation,
growth-quality, balance-sheet-risk, technicals, news-catalysts; definitions in `.claude/agents/`), each
writing `data/<T>/<agent>.md`. A citation check follows (`verify-citations`), then an
optional bear-case agent. The planner writes `data/<T>/verdict.md` confirming or overriding the suggested
label, `assemble` produces `reports/<T>-<date>.md` and rebuilds the ledger, and the report is committed.

The citation check is the hallucination guard. `verify-citations <T>` reads every agent file in `data/<T>/`
and fails an agent when a number it cites is not in `data/<T>.json` or `data/<T>.score.json`: every key in
its closing JSON block must resolve with a value within 1%, and every `(group.field)` key in its prose must
exist, with any number written just before it matching after unit normalisation (`23.1%` = 0.231, `$107.7B`
= 1.077e11). Results go to `data/<T>/citations.json`, and the report appendix shows `citation check: PASS
(5/5 agents)` or the failing agents. `run <T> --offline` re-scores today's saved snapshot without fetching.

## Disclaimer

This is generated research for the owner's own process. It is not investment advice.
