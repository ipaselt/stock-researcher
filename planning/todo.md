# Task Queue — stock-researcher

> The **pending backlog** (`⏳`). The **planner is the sole assigner AND the single writer of `planning/*.md`** —
> workers never add, reassign, or move tasks here. Each task is tagged `owner: <handle> · session: <uuid>`.
>
> Loop (canonical spec: KORTANNA §9): the planner moves a task `todo.md → progress.md` (`🔄`) **at dispatch**;
> the worker builds in `branches/<slug>/` → PR → independent review → `reviewed-pass` → merge → the planner
> moves it to `../memory/completed-tasks.md` (`✅`). Here workers are Opus sub-agents dispatched by the
> Fable planner session (manual `git worktree add branches/<slug> -b <slug>`; the built-in worktree isolation
> fails on this machine because `jq` is missing).

## Queue
*(stable `#N` IDs — never renumber. Plan v1 (#0-#6) is complete; the rows below are the backlog.)*
- ⏳ **#7** Guard follow-ups from the S6 review — (a) the SMA/EMA/RSI/MACD period exemption is too broad: `RSI 86 is overbought.` uncited passes; keep any-integer only for SMA/EMA and limit RSI/MACD to plausible periods {2, 9, 12, 14, 21, 26}; (b) inside a citation window a unitless integer range (`215-999 (analyst.target_low, analyst.target_high)`) must count as two numbers · **owner:** unassigned · branch `s7-guard-followups`
- ⏳ **#8** Research more tickers from a session rooted in this project (`/research <T>`): one sparse small-cap and one pre-profit name to exercise NOT LOOKING / L5 end to end (plan §Verification) · **owner:** planner
- ⏳ **#10** Fair-value sanity band — found on the NVDA run 2026-09-28: forward EPS 15.68 × median fiscal-year P/E 46.1 (from 100%+ growth years) = $724 vs price $230, above the analyst high target $515 and 2.2× the mean $328. Proposal: when `fair_value` exceeds `analyst.target_high`, or `fair_pe` exceeds the current `forward_pe` by more than 2×, mark `fair_pe_source` as "historical_median (regime-shifted)", set `method_fit_warning`, and have L6/L7 fall through to WAIT-with-no-target unless the planner cites a credible anchor. Keep the method transparent; do not silently clamp · **owner:** unassigned · branch `s10-fair-value-sanity`
- ⏳ **#9** `/code-review ultra` on the scoring + guard math (owner-run, optional; the owner chose to merge S2/S5 on the adversarial review alone)

## Deferred (phase 3, not planned in detail)
- Paid provider (FMP / Polygon) behind the same Protocol · batch mode (`research` over a watchlist) · dashboard
  (Streamlit, like portfolio-lab) · ETF scorecard · Agent SDK wrapper if a standalone app is ever wanted.

✅ Completed → `../memory/completed-tasks.md` (the planner moves merged tasks there on merge).
