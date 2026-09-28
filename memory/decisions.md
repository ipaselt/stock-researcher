# Decisions — stock-researcher (append-only)

## 2026-09-28 — New repo, not an extension of portfolio-lab
portfolio-lab is a Schwab holdings tracker with a research page bolted on; this is a rating engine with an
agent workflow and a resume purpose. Options: extend / wipe-and-rebuild / new. Chose new: keeps the working
tracker intact and public, and gives the researcher a clean story. Lessons (yfinance units, patterns) carried
over; no cross-project imports.

## 2026-09-28 — Claude Code native, not an Agent SDK app
Fable session orchestrates; Opus sub-agents research; Python core does data + scoring. Uses the plan, no API
key. Python core is a plain library so an SDK app can wrap it later (phase 3) if wanted.

## 2026-09-28 — yfinance now, behind a provider Protocol
Free, no key, proven in portfolio-lab. The Protocol (`providers/base.py`) is the one abstraction so a paid
API (FMP / Polygon) can be added without touching normalize/scoring. Pinned to 1.5.1; fixtures + a live
canary test are the breakage alarm.

## 2026-09-28 — Hybrid rating: deterministic scorecard + Fable verdict
Pure rules are rigid on edge cases; pure LLM judgment is not reproducible or defensible in an interview.
The scorecard (weights, bands, coverage) and label rules L1-L8 are code + docs; Fable confirms or overrides
with rule id + cited reason; both labels are kept in the ledger.

## 2026-09-28 — Long-term lens, momentum weighted 10%
Horizon 1-5 years. Momentum is a timing input (WAIT target), not a quality input.

## 2026-09-28 — Single Fable session + Opus sub-agents (not multi-session)
Kortanna's lightest rung that fits. The multi-session rung (worker sessions the human launches, `.planner`
lock) would block the planner from running pytest for review and add babysitting. `.orchestrated` is kept so
main stays merge-only and the reviewed-pass merge gate applies. Reviewer sub-agent runs on Opus via the
Agent tool's model override; Fable reads the findings.

## 2026-09-28 — Agents write their own files; reports are assembled mechanically
To keep Fable's context small: each research agent writes `data/<T>/<agent>.md` and returns a short JSON
summary; `assemble` stitches agent files + Fable's short `verdict.md` into the report.

## 2026-09-28 — Ledger derived from report front-matter
`main-protection` allows only `.md` commits on main outside PRs. Reports are `.md` with YAML front-matter;
`reports/ratings.csv` is regenerated from them (gitignored), so a research run commits without a PR.
