# Plan — stock-researcher (new project)

## Context
The user wants to restart stock research as a fresh, resume-worthy project: a stock research and rating
engine run as a small "research firm." A Fable planner session orchestrates Opus sub-agents, each with one
research job; their findings come back to Fable, which reviews them and issues a verdict. The existing
`projects/portfolio-lab/` stays as-is (holdings tracker); this is a separate sibling project.

Decisions locked with the user (2026-09-28):
| Decision | Choice |
|---|---|
| Relationship to portfolio-lab | New separate project `projects/stock-researcher/`; reuse lessons, not code |
| Architecture | Claude Code native: Fable orchestrates, Opus sub-agents research; Python core for data + scoring |
| Data source | yfinance now, behind a swappable provider interface so a paid API key can slot in later |
| Rating method | Hybrid: transparent weighted scorecard + Fable's written verdict |
| Horizon | Long-term, 1 to 5 years; technicals inform entry timing only |
| Phase-one output | Markdown report per ticker, saved in the repo |
| Universe | US-listed common stocks |
| Build model | Opus workers write code, Fable plans and reviews, independent review before merge |
| Ratings vocabulary | BUY · SELL · WAIT (with target entry price) · HAS RUN · NOT LOOKING |

Defaults taken unless the user objects: repo name `stock-researcher`, public on GitHub under ipaselt;
five research agents (valuation · growth & quality · balance sheet & risk · technicals · news & catalysts).

### Verified: the Opus-for-workers premise
- Sub-agent model pinning is official: `model: opus` in the agent file's frontmatter (aliases sonnet/opus/haiku/fable, full IDs, or `inherit`). Source read: code.claude.com/docs/en/sub-agents.
- Official costs doc says sub-agent requests "still draw on your usage" and that choosing a smaller model for a sub-agent is the way to "spend less on them." Source read: code.claude.com/docs/en/costs.
- **Not stated anywhere official:** whether plan usage limits are metered by raw tokens or by model cost. So "Opus workers spend less" is endorsed in direction but unquantified. Treat it as a cost reduction, not a guarantee of Fable-usage isolation.

## Build workflow (how the project gets built)
Kortanna's "lightest rung that fits": **one Fable session + Opus sub-agents**, not the multi-session
planner/worker/reviewer setup (that rung needs you to launch and babysit separate sessions, and its planner
lock would stop me running pytest to review). Concretely:
1. I (Fable) hold the plan, write only `.md` brain files directly to main, and dispatch one task at a time.
2. Each task goes to an **Opus worker sub-agent** (`model: opus`, `isolation: worktree`; the existing
   WorktreeCreate hook places it under `branches/<task>/`). It builds, runs the task's verify command, commits
   on its branch, and opens a PR.
3. An **adversarial-reviewer sub-agent** (existing type, `model: inherit` = Fable) reviews the diff. I read the
   review and the tests myself, fix or send back, label `reviewed-pass`, merge. The repo carries
   `.orchestrated`, so the existing hooks enforce merge-only main and the reviewed-pass merge gate.
4. Critical-surface triggers per review-before-push (indicator/scoring math counts as "data fidelity"): I
   will flag when a slice deserves your paid `/code-review ultra` before merge, and leave that to you.
5. Not creating the `.planner` marker or a dev-root plan-mode setting: those belong to the multi-session rung.

Stamping steps come from `guide-setup/method/templates/new-project/setup-checklist.md`: copy
`projects/_template`, `git init`, `gh repo create stock-researcher --public --source=. --remote=origin`,
`gh repo edit --delete-branch-on-merge`, the four review labels, rich `CLAUDE.md` from the template, first
commit + the documented one-time `.review-ready` touch for the scaffold push.

Token-saving refinements on top of the method (all three push work to the cheapest layer):
- Research agents **write their own** `data/<T>/<agent>.md` and return only a short JSON summary, so Fable
  never carries five full reports in context.
- `python -m stock_researcher assemble T` stitches agent files + Fable's short `verdict.md` into the report
  mechanically. Fable writes ~150 words per run, not the whole document.
- The adversarial-reviewer runs with the Agent tool's `model: "opus"` override; Fable reads the findings.

## Repo layout (`projects/stock-researcher/`)
```
CLAUDE.md · CONTEXT.md · .orchestrated · .gitignore (.venv data/ branches/ reports/ratings.csv)
pyproject.toml            — deps (yfinance==1.5.1, pandas, pytest); pytest: pythonpath=".", addopts="-m 'not live'"
README.md                 — resume-facing: what it is, sample report, how the scorecard works
docs/scorecard.md · fair-value.md · labels.md   — the methodology (interview handout); a test keeps docs = code
.claude/commands/research.md                    — /research <TICKER> orchestration (Fable runs this)
.claude/agents/{valuation,growth-quality,balance-sheet-risk,technicals,news-catalysts,bear-case}.md  — model: opus
stock_researcher/
  __main__.py · cli.py     — subcommands: run · snapshot · score · assemble · verify-citations · ledger
  providers/base.py        — DataProvider Protocol (the ONLY abstraction); providers/yfinance_provider.py
  snapshot.py              — Snapshot dataclass (groups: meta valuation growth profitability health performance
                             dividend analyst technical ownership events) + JSON in/out
  normalize.py             — FIELDS table: info_key → group.field + unit code (raw/frac/pct/usd/str); sanity warnings
  technicals.py            — sma, rsi, relative_strength, period returns, max drawdown, CAGR (pure pandas)
  scorecard.py             — METRICS bands + weights, renormalization, coverage → ScoreResult
  fair_value.py · labels.py — fair value / entry price; label rules L1-L8
  report.py · ledger.py · citations.py
tests/  conftest.py (FakeProvider + autouse no-network guard) · fixtures/ (AAPL, sparse, negative-EPS, unknown)
        one test file per module · test_docs.py · test_agent_files.py · test_live.py (@pytest.mark.live)
data/<T>.json · data/<T>.score.json · data/<T>/<agent>.md · data/<T>/verdict.md   — gitignored run artifacts
reports/<T>-<YYYY-MM-DD>.md (committed, YAML front-matter = ledger source) · reports/ratings.csv (derived)
planning/ · memory/ · branches/   — Kortanna board and worktrees
```
Patterns copied (not imported) from portfolio-lab: `src/research/fundamentals.py` FIELDS + format codes,
`technicals.py` sma/rsi/relative_strength, `tests/test_technicals.py` synthetic-series style.

## Data model
- Every numeric field `float | None`; ratios stored as **fractions or multiples, never percents**.
- Unit codes: `pct` (divide by 100) for `dividendYield` and `debtToEquity` only; `frac` for margins, growth,
  ROE/ROA, payout, holder pcts, 52-week changes; `raw` for multiples, prices, counts; `usd` for cash amounts.
- Derived: fcf_yield, earnings_yield, fcf_margin, net_debt, cash_to_debt, interest_coverage (EBIT / interest
  expense from income_stmt), revenue/EPS CAGR 3y & 5y (income_stmt), returns YTD/1y/3y/5y + vs SPY, max
  drawdown, pct from 52w high/low, price vs SMA50/200, RSI14. `safe_div`: any None in → None out.
- Missing: None → `meta.fields_missing`; sanity guards append `meta.warnings` (dividend_yield > 0.25,
  debt_to_equity > 50, any frac > 5, forward_pe < 0) so a future yfinance unit flip trips the live smoke test.
- Unknown ticker (no currentPrice and no regularMarketPrice) → `TickerNotFound`, CLI exit 2.

## Scorecard (long-term quality-at-a-reasonable-price; absolute bands; A=10 B=7.5 C=5 D=2.5 F=0)
| Category (wt) | Metrics (wt) and A / F band edges |
|---|---|
| Valuation (30) | forward_pe (10) A<15 F>45; peg (8) A<1.0 F>4; ev_ebitda (6) A<10 F>30; fcf_yield (6) A>6% F<1% |
| Growth (20) | revenue_growth_yoy (6) A>20% F<0; revenue_cagr_3y (6) A>15% F<0; earnings_growth_yoy (4) A>20% F<-10%; eps_cagr_3y (4) A>15% F<0 |
| Profitability (20) | gross_margin (4) A>55% F<20%; operating_margin (6) A>25% F<5%; roe (6) A>25% F<5%; fcf_margin (4) A>20% F<0 |
| Health (20) | debt_to_equity (6) A<0.3x F>2.0x; current_ratio (4) A>2.0 F<0.8; interest_coverage (6) A>15x F<1.5x; cash_to_debt (4) A>1.0 F<0.1 |
| Momentum (10) | rel_1y vs SPY (5) A>+15pts F<-15; price_vs_sma200 (5) A 0..+20% F<-25% |
Full B/C/D bands live in `docs/scorecard.md` (the design pass has them; the worker copies them in).
Math: metric points × weight, summed over **covered** metrics, renormalized to 0-100; `coverage_pct` = covered
weight. Bands for prose: ≥75 strong · 60-74 good · 45-59 mixed · <45 weak. Momentum is small on purpose: for a
1-5y holder price action is a timing input, not a quality input (the interview line).

**Fair value / entry price (one explainable method):** `fair_value = forward_eps × fair_pe`, where fair_pe =
median year-end P/E over the last 3-5 fiscal years (needs ≥3 positive-EPS years, else a documented per-sector
default; source recorded). Band ±15%. Margin of safety tiered by quality: score ≥75 → 5%, 60-74 → 15%,
<60 → 20%; `entry_price = fair_value × (1 − mos)`. Negative/near-zero EPS → None with reason. Limits printed
in every report (banks/REITs/cyclicals/pre-profit).

**Label rules (first match wins; rule id is written to the report and ledger):**
L1 coverage<60% → NOT LOOKING (data) · L2 health score<30 → NOT LOOKING (balance sheet) · L3 score<45 and
price>fv×1.15 → SELL · L4 score<55 → NOT LOOKING · L5 no fair value → NOT LOOKING (Fable may override for
growth names) · L6 price≤entry → BUY · L7 price>fv×1.15 and (≤5% from 52w high or 1y return ≥40%) → HAS RUN
· L8 else → WAIT with entry target. Fable confirms or overrides; an override needs rule id + new label + one
sentence citing a snapshot number or agent finding. Ledger stores both `label_suggested` and `label_final`.

## Agent roster (`.claude/agents/`, all `model: opus`, `effort: high`)
Agents never run Python or fetch prices; they read `data/<T>.json` + `data/<T>.score.json` and may cite only
numbers present there, with the key in parentheses, e.g. `forward P/E 28.1x (valuation.forward_pe)`.
Each writes exactly one file `data/<T>/<agent>.md` (fixed headings: Findings · Assessment · Risks · Grade +
Confidence · fenced JSON block with `numbers_cited`) and returns only that JSON block.
| Agent | Reads | Tools |
|---|---|---|
| valuation | meta valuation analyst dividend score.fair_value; flags `method_fit:ok/poor` | Read Write |
| growth-quality | meta growth profitability ownership | Read Write |
| balance-sheet-risk | meta health profitability dividend | Read Write |
| technicals | meta performance technical (entry window for a 1-5y holder) | Read Write |
| news-catalysts | meta events analyst; last ~90 days; external facts need a URL; no new financial metrics | Read Write WebSearch WebFetch |
| bear-case (phase 2) | snapshot + the five agent files; steel-mans the short thesis | Read Write |

## `/research <TICKER>` flow (`.claude/commands/research.md`, `argument-hint: [TICKER]`)
1. Validate `$0`. 2. `python -m stock_researcher run T` → snapshot, score, skeleton report. Exit 2 → stop.
3. Fable reads `data/T.score.json` (score, coverage, suggested label + rule). 4. Fan out the five agents in one
message. 5. `verify-citations T` → any agent whose cited numbers don't match the snapshot (1% tolerance) is
re-run or dropped. 6. Optional bear-case. 7. Fable writes `data/T/verdict.md` (label confirm/override + reason,
≤150-word thesis, entry target, top 3 risks, what changes my mind, triggers). 8. `assemble T` → final
`reports/T-<date>.md` with YAML front-matter (date ticker price score coverage fair_value entry
label_suggested label_final). 9. `ledger` regenerates `reports/ratings.csv` from all report front-matter
(derived, so runs commit only `.md` and stay hook-compliant on main). 10. Print a 5-line summary.
Report sections: header · verdict box · scorecard table · fair value derivation · five agent sections ·
bear case · synthesis · appendix (missing fields, warnings, citation check, methodology links, disclaimer).

## Slices (one Opus worker PR each; Goal · Done-looks-like · Verify-by)
| # | Slice | Verify-by |
|---|---|---|
| S0 | Scaffold: Kortanna stamp, git + public remote + labels, pyproject, `.venv`, empty package, smoke test | `pytest` green; `python -m stock_researcher --help` exits 0; scaffold pushed |
| S1 | Data layer: provider Protocol + yfinance provider + fixtures captured (AAPL, sparse, negative-EPS, unknown) + FakeProvider/no-network guard + snapshot/normalize + technicals + `snapshot` CLI | unit regressions per gotcha (0.32→0.0032, 78.4→0.784, frac unchanged, None tracking, warnings); unknown → TickerNotFound; synthetic-series technicals; guard proves no network |
| S2 | Scoring: scorecard + fair value + labels + `score` CLI | all-A → 100, all-F → 0, dropped metric renormalizes, parametrized band edges; fair-value 5/3/2-year + sector fallback + negative EPS; one test per rule L1-L8 + precedence |
| S3 | Output: report skeleton + assemble + front-matter + derived ledger + `run` CLI + docs (scorecard/fair-value/labels/README) | 12 headings in order; ledger rebuild from N reports; `run` with FakeProvider writes all files; `test_docs.py` asserts every metric + weight in code appears in docs |
| S4 | Agents + command: five agent files, shared contract, `research.md` | `test_agent_files.py` (frontmatter: model opus, tool whitelist); **first live `/research AAPL`**, Fable reviews the report (manual acceptance) |
| S5 | Guards: `verify-citations`, bear-case agent, provider retry/backoff, `--offline`, `test_live.py` | fabricated number fails / matching passes; `pytest -m live` passes when run by hand |
| S6 | Resume polish: sample report committed, README walkthrough, console score table | README links resolve; `pytest` green |
Phase 3 (deferred): FMP/Polygon provider behind the same Protocol; batch mode; dashboard.
Critical-surface flag: S2 (scoring math = data fidelity). I'll recommend `/code-review ultra` on S2 before merge.

## Verification (whole initiative)
- Every slice: worker runs `pytest` in its worktree and shows output; Opus adversarial review; I read the diff
  and rerun `pytest` on the branch before labelling `reviewed-pass` and merging.
- End-to-end: `/research AAPL` after S4 produces `reports/AAPL-<date>.md` with a filled scorecard, five agent
  sections whose numbers pass `verify-citations`, a verdict with rule id, and a ledger row. Then one sparse
  small-cap and one pre-profit name to exercise NOT LOOKING / L5.
- `pytest -m live` once at the end as the yfinance canary.

## Risks
yfinance breakage (pin 1.5.1, one provider file, fixtures, live canary, unit warnings) · rate limits (~6 calls
per run, retry, `--offline`) · hallucinated numbers (JSON-only inputs, mandatory citations, `verify-citations`)
· false precision (every threshold documented, docs = code test, coverage printed, limits in every report) ·
fair value wrong lens for banks/REITs/pre-profit (None + `method_fit:poor` + L5) · Windows paths/encoding
(`pathlib`, utf-8 everywhere, CLI tested via `main([...])`).

## Not investment advice
Reports carry a standing disclaimer. The tool produces research ratings for the user's own process; I don't
recommend trades.
