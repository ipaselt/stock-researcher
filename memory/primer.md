# Primer — stock-researcher
*Rewrite each session. Last updated: 2026-09-28.*

## State
- **Stamped 2026-09-28** from `projects/_template` (orchestrated, merge-only main). Plan v1 approved the same
  day: `planning/plans/stock-researcher-v1.md` — seven slices S0-S6, Opus workers build, Fable plans/reviews.
- **S0 scaffold done 2026-09-28**: Python 3.11.9 `.venv` (no `py` launcher on this machine — use
  `python -m venv`), yfinance 1.5.1, pandas 3.0.6 (unpinned major; cap `<4` only if a slice needs 2.x
  behaviour), stub CLI with six subcommands, 3 smoke tests. Scaffold commit on main; public remote
  `ipaselt/stock-researcher`; review labels created.
- **S1 data layer merged 2026-09-28 (PR #1, f22eafc)**: `python -m stock_researcher snapshot AAPL` works live
  (1 field missing: `health.interest_coverage` — Apple reports no interest expense). 99 offline tests.
  Fixture tickers: AAPL, SPY, HCMC (sparse OTC), RIVN (negative EPS), ZZZZZZ (unknown). `normalize()` returns
  `(groups, warnings)`; `fields_missing` is computed on the final Snapshot as `group.field` paths.
  `revenue_cagr_5y` does not exist (yfinance gives a 4-year span).
- **S2 scoring merged 2026-09-28 (PR #2, 31cc8b6)**: `score AAPL` → 60.1 (good), coverage 94%, fair value
  295.06 (median fiscal-year P/E 30.78 over 4 years), entry 250.80, HAS RUN (L7). 370 tests. The B/C/D band
  edges are ratified (decisions.md) and pinned by a golden test. Owner chose to merge without the ultra pass.
- **S3 output merged 2026-09-28 (PR #3, c164079)**: `run` → skeleton; `assemble` → `reports/<T>-<date>.md`
  (front-matter is the ledger source; verdict.md validated, override needs a reason); `ledger` rebuilds
  `ratings.csv`. Docs in `docs/` are test-pinned to the code. 453 tests.
- **S4 agents + command merged 2026-09-28 (PR #4, 41bcb50)**: `.claude/agents/{valuation,growth-quality,
  balance-sheet-risk,technicals,news-catalysts,bear-case}.md` + `.claude/commands/research.md`. 469 tests.
  **Gotcha:** project agents/commands register only in a session rooted INSIDE `projects/stock-researcher/`;
  from the dev-root planner session, dispatch them as `general-purpose` + `model: opus` with "read your role
  file first" (what the first live AAPL pass did).
- **S5 guards merged 2026-09-28 (PR #5, e578465)**: `verify-citations` is the hallucination guard (JSON block +
  window-wide prose numbers + uncited-number rule; agent contract v1.1 = same-sentence citations, signs as
  stored); `run --offline`; provider retry; `pytest -m live` canaries (NVDA fiscal-year P/E split-consistent).
  548 offline tests.
- **AAPL report citation-verified 2026-09-28** (`reports/AAPL-2026-09-28.md`, 2b1f4db): HAS RUN (L7), entry
  250.80, `citation check: PASS (5/5)`. Lesson: agents written under v1.0 fail v1.1 on uncited numbers; one
  re-dispatch with the failure lines fixes it.
- **S6 polish dispatched 2026-09-28** (last planned slice).

## Verified facts (don't re-derive)
- yfinance 1.5.1 live AAPL run 2026-09-28: every planned metric present except `ytdReturn` (fund field →
  compute from history). Unit gotchas in `CONTEXT.md`.
- `model: opus` in an agent file's frontmatter pins the sub-agent model (docs: sub-agents). Docs say cheaper
  sub-agent models "spend less" but do not state how plan limits are metered — direction verified, magnitude not.
- `gh` is authenticated as ipaselt; `stock-researcher` was free as a repo name on 2026-09-28.

## Next
Dispatch #1 S1 data layer (Opus worker in `branches/s1-data-layer/`), then S2 scoring (flag `/code-review ultra`).
