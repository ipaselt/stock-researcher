# stock-researcher — CONTEXT.md

Working detail for this project (`projects/stock-researcher/`). Last updated: 2026-09-28.

> Lean instance of KORTANNA §9. The approved design is `planning/plans/stock-researcher-v1.md` — read it
> before touching scoring, agents, or the report format.

## What to Load
| Task | Load | Skip |
|------|------|------|
| Resume / "what's next" | `memory/primer.md` + `planning/progress.md` → else your assigned `⏳` in `planning/todo.md` | others' tasks |
| Cross-session state | `memory/primer.md` → `memory/decisions.md` | code |
| Any slice S1-S6 | `planning/plans/stock-researcher-v1.md` (the slice's row + the relevant design section) | other slices |
| Touching yfinance keys or units | `stock_researcher/normalize.py` + `tests/test_normalize.py` | scoring |
| Touching thresholds / weights / labels | `stock_researcher/scorecard.py`, `fair_value.py`, `labels.py` + `docs/*.md` (keep in sync; `test_docs.py` checks) | agents |
| Touching the research flow | `.claude/commands/research.md` + `.claude/agents/*.md` | Python core |

## The Process
**Worker startup:** read `CLAUDE.md` (L1) + this file (L2) + your task's row in the plan. The generic worker
contract (startup sequence, tool ladder, JSON result) is
`~/Developer/guide-setup/method/templates/execution-workers/base.md`.

Run by **one planner session (Fable)** that dispatches **Opus worker sub-agents**. The planner moves a slice
`todo.md → progress.md` at dispatch; the worker builds in `branches/<slug>/` → runs the slice's Verify-by →
PR labelled `needs-review` → an independent adversarial review → the planner reads the review, reruns the
tests, labels `reviewed-pass`, and merges. Production code reaches `main` only via merge (S0's scaffold commit
is the documented exception). Workers never edit `planning/*.md`.

**Research runs** (`/research <TICKER>`) are planner-driven: Python writes `data/`, agents write
`data/<T>/<agent>.md`, Fable writes `data/<T>/verdict.md`, `assemble` produces `reports/<T>-<date>.md`.
Reports are `.md`, so a run commits straight to main.

## Gotchas (carry-overs from portfolio-lab, verified live 2026-09-28 on yfinance 1.5.1)
- `dividendYield` is pre-multiplied (0.32 = 0.32%); `debtToEquity` is a percent (78.4 = 0.78x); margins,
  growth, ROE/ROA, payout, holder percentages, `52WeekChange` are fractions.
- `ytdReturn` is null for common stocks (fund field) — compute period returns from `.history()`.
- Unknown tickers return a near-empty `info` dict: check `currentPrice` and `regularMarketPrice` both None.
- `.news` items nest under `content` (`title`, `summary`, `pubDate`, `canonicalUrl.url`, `provider.displayName`).
- `income_stmt` gives 5 annual columns (most recent first); rows include Total Revenue, Net Income, Diluted
  EPS, EBIT, Interest Expense.
- Only the cwd's `.claude/` loads: project agents/commands live in `.claude/` here, not at the dev root.

## Skills & Tools
| Skill / Tool | When | Purpose |
|--------------|------|---------|
| Agent tool, `model: "opus"` | dispatching a slice or a research agent | Opus workers; Fable stays the planner |
| `adversarial-reviewer` sub-agent (Opus override) | every PR before merge | independent review of the diff |
| `/code-review ultra` (human-run) | scoring-math slices (S2) | paid deep review before merge |

## What NOT to Do
- Workers: never commit code to `main` (merge-only); never touch a `🔄` (in-progress) task.
- Never let an agent fetch prices or compute ratios — data comes from the Python core only.
- Never hand-edit `reports/ratings.csv` or `data/`.
- Never hardcode secrets.
