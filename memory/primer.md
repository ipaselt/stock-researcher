# Primer — stock-researcher
*Rewrite each session. Last updated: 2026-09-28.*

## State
- **Stamped 2026-09-28** from `projects/_template` (orchestrated, merge-only main). Plan v1 approved the same
  day: `planning/plans/stock-researcher-v1.md` — seven slices S0-S6, Opus workers build, Fable plans/reviews.
- **S0 scaffold done 2026-09-28**: Python 3.11.9 `.venv` (no `py` launcher on this machine — use
  `python -m venv`), yfinance 1.5.1, pandas 3.0.6 (unpinned major; cap `<4` only if a slice needs 2.x
  behaviour), stub CLI with six subcommands, 3 smoke tests. Scaffold commit on main; public remote
  `ipaselt/stock-researcher`; review labels created.
- Nothing researched yet. No reports, no fixtures.

## Verified facts (don't re-derive)
- yfinance 1.5.1 live AAPL run 2026-09-28: every planned metric present except `ytdReturn` (fund field →
  compute from history). Unit gotchas in `CONTEXT.md`.
- `model: opus` in an agent file's frontmatter pins the sub-agent model (docs: sub-agents). Docs say cheaper
  sub-agent models "spend less" but do not state how plan limits are metered — direction verified, magnitude not.
- `gh` is authenticated as ipaselt; `stock-researcher` was free as a repo name on 2026-09-28.

## Next
Dispatch #1 S1 data layer (Opus worker in `branches/s1-data-layer/`), then S2 scoring (flag `/code-review ultra`).
