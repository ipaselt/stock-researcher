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
.venv/Scripts/python.exe -m stock_researcher score AAPL --table  # ... plus the full scorecard as a text table
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
its closing JSON block must resolve with a value within 1%, every `(group.field)` key in its prose must
exist, every number written between the previous citation and a key must match it after unit normalisation
(`23.1%` = 0.231, `$107.7B` = 1.077e11), and a decimal or unit-bearing number with no citation in its sentence
fails. The JSON block's `reason` and `flags` get the same prose check. Results go to `data/<T>/citations.json`;
the report appendix shows `citation check: PASS (5/5 agents)` or the failing agents, whose sections are
withheld. `run <T> --offline` re-scores today's saved snapshot without fetching.

## Sample report

[reports/AAPL-2026-09-28.md](reports/AAPL-2026-09-28.md) is a real run, with all five agents passing the
citation check. Its verdict table:

| Item | Value |
|---|---|
| Suggested label | HAS RUN (L7) |
| Score | 60.1/100 (good) |
| Coverage | 94% |
| Fair value | $295.06 (band $250.80 – $339.32) |
| Entry target | $250.80 |
| Upside to fair value | -13.3% |

HAS RUN (rule L7) means a decent business whose price ($340.15) already sits above the top of its own
fair-value band while trading within 5% of its 52-week high: don't chase it, and new money waits for the
$250.80 entry target. The planner confirmed the rule's label rather than overriding it.

## Website

Every committed report and the three methodology pages are published as a static Next.js site from `web/` on
Vercel. It is built at deploy time from `reports/*.md` (front-matter drives the index) and `docs/*.md`: no live
data, no API, no environment variables. Every push to `main` redeploys, so `/research` pushes its report commit.

Run it locally (port 3001):

```bash
cd web && npm install && npm run dev
```

Deploy on Vercel: Add New → Project → import this repository; set **Root Directory** to `web`; keep **"Include
source files outside of the Root Directory"** on (the build reads `../reports` and `../docs`); framework preset
Next.js; no environment variables. Deploy.

## A run, step by step

`/research AAPL` ends by printing five lines — for the sample run, in the shape the command prescribes:

```
Label: HAS RUN — confirms the suggested HAS RUN (L7), no override
Score: 60.1/100 (good), coverage 94%
Fair value: $295.06 (band $250.80 – $339.32); entry target $250.80
Thesis: a high-quality, cash-generative franchise whose stock has already priced in its best year in some time
Report: reports/AAPL-2026-09-28.md
```

What each artifact on the way there is:

- `data/AAPL.json` — the snapshot: every ratio normalized to a fraction or a multiple (prices, dollar
  amounts, dates and text pass through), plus the fields that were missing and any warnings.
- `data/AAPL.score.json` — the 18 metrics (grade, points, note; a skipped metric shows why), the five category scores, the total and coverage, the fair
  value with its method and inputs, and the suggested label with the rule that fired (`score AAPL --table`
  prints it as a table).
- `data/AAPL/skeleton.md` — the report with the header, verdict table, scorecard and fair value already
  filled in, and an empty slot per agent section and for the planner's verdict.
- `data/AAPL/<agent>.md` — each analyst's section: findings, an assessment, and a closing JSON block listing
  every number it cited with its key.
- `data/AAPL/citations.json` — `verify-citations` output: PASS, or the exact mismatches, per agent.
- `data/AAPL/verdict.md` — the planner's final label, entry target, override reason (`none` here), thesis,
  risks and what would change its mind.
- `reports/AAPL-2026-09-28.md` — the assembled report; its YAML front-matter is the ledger row.
- `reports/ratings.csv` — the ledger, rebuilt from every report's front-matter, keeping both the suggested and
  the final label.

`data/` is regenerated on every run and never committed; `reports/` is the permanent record.

## Design choices worth asking me about

- **Absolute bands, not sector-relative ones:** a forward P/E of 40 is expensive whatever the peers trade at,
  so a sector-wide bubble cannot make a stock look cheap, and a score needs no peer data to reproduce.
- **Momentum is only 10%:** over a 1-5 year horizon price action says when to act, not whether the business
  is good, so at full coverage trend alone can move the total by at most 10 points
  ([docs/scorecard.md](docs/scorecard.md)).
- **Fair value uses the company's own median P/E:** the median year-end P/E of its last 3-5 profitable fiscal
  years anchors to how the market has actually priced this business (the median so one distorted year cannot
  move it), with a sector default only when fewer than 3 such years exist ([docs/fair-value.md](docs/fair-value.md)).
- **The label rule is code and every override is logged:** rules L1-L8 pick the label mechanically; the
  planner may override only with the rule id, the new label and one cited reason, `assemble` refuses a
  silent change, and both labels land in the ledger so the rules' hit rate can be measured
  ([docs/labels.md](docs/labels.md)).
- **Agents cite instead of compute:** every number an agent writes must be in the snapshot or score file with
  its key beside it, and `verify-citations` fails the agent on a wrong or dishonestly rounded value, an
  uncited decimal or percentage, an integer next to a metric word (`RSI is 86`), a range bound
  (`12-38x`), or numbers attributed to the wrong key when several keys share one parenthesis — so the report
  cannot contain an invented decimal, percentage, multiple or dollar amount without the check saying so; plain
  integers away from metric words, unitless ranges and version numbers are the documented exemptions.

## Disclaimer

This is generated research for the owner's own process. It is not investment advice.
