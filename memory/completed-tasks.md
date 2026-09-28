# Completed — stock-researcher (✅ archive, newest first)

*(The planner moves merged tasks here from `../planning/progress.md`.)*

- ✅ **research: AAPL (re-verify)** — 2026-09-28 (2b1f4db). Under contract v1.1 three analysts failed the
  citation check (uncited numbers; one mis-windowed citation); re-dispatched once with the failure lines, all
  five PASS; report re-assembled with `citation check: PASS (5/5 agents)`. Label unchanged: HAS RUN (L7).
- ✅ **#5** S5 Guards — 2026-09-28, PR #5 merged (e578465). `verify-citations` (JSON block strict 1%; prose:
  window-wide numbers before each citation, unit-normalised, uncited decimal/unit numbers FAIL, reason/flags
  checked), `citations.json` → report appendix, `assemble` withholds FAIL sections; provider retry 1s/2s (incl.
  empty history); `run --offline`; `test_live.py` (AAPL canary, NVDA split-consistency PASSED: fiscal-year P/E
  38.9/40.7/51.6/111.9, unknown ticker). Agent contract v1.1 (same-sentence citations, signs as stored);
  command re-verifies after the bear case. 548 tests. Review: 3 MAJORs on the guard closed; round-2 ×1.5
  mutation loop 100% caught.
- ✅ **research: AAPL** — 2026-09-28, first live pass (S4 acceptance). `run` → five Opus analysts (dispatched as
  general-purpose + role file from the dev-root session) → planner verdict → `assemble` → `reports/AAPL-2026-09-28.md`
  (04d1a76), ledger 1 row. Result: 60.1 / good / 94% / HAS RUN (L7) confirmed, entry 250.80. No assembly
  warnings. Citation check not yet available (S5).
- ✅ **#4** S4 Agents + command — 2026-09-28, PR #4 merged (41bcb50). Six Opus agent definitions transcribed
  from `planning/research/agent-contract.md`, `.claude/commands/research.md` from `research-command.md`
  (v1.1: owner-only invocation, scoped report commit, bear-case inputs), `test_agent_files.py` anchored to the
  spec. 469 tests. Review: SHIP against the official sub-agent / slash-command docs.
- ✅ **#3** S3 Output — 2026-09-28, PR #3 merged (c164079). `report.py` (12-section skeleton, slot markers,
  `assemble` with verdict validation and the override protocol), `ledger.py` (ratings.csv rebuilt from report
  front-matter), CLI `run` / `assemble --date` / `ledger`, docs (scorecard, fair-value, labels, README) with
  `test_docs.py` pinning every edge/weight/constant. 453 tests. Review MAJOR (stale agent files reused on
  rerun) fixed: `run` clears `data/<T>/*.md`, `assemble` ignores files older than the skeleton.
- ✅ **#2** S2 Scoring — 2026-09-28, PR #2 merged (31cc8b6). One METRICS table (18 metrics, 5 categories,
  weights 30/20/20/20/10), one `grade()`, documented special cases; fair value = forward EPS × median
  fiscal-year P/E (≥3 years, else sector default), ±15% band, tiered margin of safety, near-zero-EPS floor;
  labels L1-L8; `score` CLI. 370 tests incl. a golden table pinning every edge and weight. Review: SHIP, AAPL
  numbers reproduced by hand (60.1 / good / HAS RUN L7 / entry 250.80); 5 surviving mutations closed in the
  hardening commit. Merged on the owner's instruction without the ultra pass.
- ✅ **#1** S1 Data layer — 2026-09-28, PR #1 merged (f22eafc). Provider Protocol + yfinance provider, FIELDS
  unit table, Snapshot with derived fields, technicals, `snapshot` CLI, fixtures (AAPL, SPY, HCMC sparse, RIVN
  negative-EPS, ZZZZZZ unknown), FakeProvider + no-network guard, 99 tests. Review round 1 found 3 MAJORs
  (unpinned fraction keys, TTM/fiscal mismatch in fcf_margin, fields_missing semantics) — all fixed and
  confirmed in round 2. Deferred to S2: zero-debt handling for cash_to_debt / interest_coverage.

- ✅ **#0** S0 Scaffold — 2026-09-28. Kortanna stamp (orchestrated, merge-only main), brain files, plan v1 saved
  to `planning/plans/`, Python 3.11.9 `.venv` with yfinance 1.5.1 + pandas 3.0.6, `pyproject.toml`, stub CLI
  with the six subcommands, 3 smoke tests green. Built by an Opus worker, reviewed by the planner, landed as
  the documented scaffold commit; public remote `ipaselt/stock-researcher` + review labels.
