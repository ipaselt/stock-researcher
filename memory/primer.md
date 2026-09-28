# Primer — stock-researcher
*Rewrite each session. Last updated: 2026-09-28 (end of the build day).*

## State
- **Plan v1 COMPLETE 2026-09-28** — stamped, built, and shipped in one day: six PRs (S1-S6) each built by an
  Opus worker in a manual worktree, reviewed by an Opus adversarial-reviewer sub-agent (every review found
  something real; S6 round 1 was a DO-NOT-SHIP that was reworked), merged by the planner. Public repo
  `ipaselt/stock-researcher`, main at 08a9ee8, **583 offline tests + 3 live canaries**.
- **What works end to end:** `run <T>` (snapshot → scorecard → fair value → label → skeleton) → five Opus
  analysts write `data/<T>/<agent>.md` → `verify-citations <T>` (the hallucination guard, agent contract v1.2)
  → planner writes `data/<T>/verdict.md` → `assemble <T>` → `reports/<T>-<date>.md` + `ratings.csv`.
  Sample: `reports/AAPL-2026-09-28.md` — 60.1 / good / 94% / **HAS RUN (L7)**, entry 250.80,
  `citation check: PASS (5/5 agents)`.
- **How to research from here:** open a session rooted in `projects/stock-researcher/` and type
  `/research <TICKER>` (the command and the six agents register only there). From the dev-root planner,
  dispatch each agent as `general-purpose` + `model: opus` + "read your role file first" instead.
- **Docs = code:** `docs/scorecard.md`, `fair-value.md`, `labels.md` are pinned by `tests/test_docs.py`; the
  agent files are pinned to `planning/research/agent-contract.md` by `tests/test_agent_files.py`.

## Verified facts (don't re-derive)
- yfinance 1.5.1 units: `dividendYield` and `debtToEquity` are percents, everything else fractions; `ytdReturn`
  is null for stocks; unknown tickers give a near-empty `info`; annual `Diluted EPS` IS split-restated (NVDA
  fiscal-year P/E 38.9 / 40.7 / 51.6 / 111.9 — no 10× jump).
- `model: opus` in an agent frontmatter pins the sub-agent model; docs say cheaper sub-agent models "spend
  less" but do not state how plan limits are metered.
- `jq` is missing on this machine: every `~/.claude/hooks` guard exits 0 silently and `isolation: worktree`
  fails; review/merge gating is discipline. Fix: `winget install jqlang.jq`.
- Agents written under an older contract fail a stricter guard on uncited numbers; one re-dispatch with the
  failure lines quoted fixes them (happened twice today: v1.0→v1.1 for three agents, v1.1→v1.2 for one).

## Next
Backlog in `planning/todo.md`: #7 guard follow-ups (RSI period exemption, unitless ranges in a window),
#8 research a sparse small-cap and a pre-profit name from an in-project session, #9 optional ultra review.
Phase 3 ideas (paid provider, batch mode, dashboard) are deferred.
