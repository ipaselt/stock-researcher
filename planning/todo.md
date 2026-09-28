# Task Queue — stock-researcher

> The **pending backlog** (`⏳`). The **planner is the sole assigner AND the single writer of `planning/*.md`** —
> workers never add, reassign, or move tasks here. Each task is tagged `owner: <handle> · session: <uuid>`.
>
> Loop (canonical spec: KORTANNA §9): the planner moves a task `todo.md → progress.md` (`🔄`) **at dispatch**;
> the worker builds in `branches/<slug>/` → PR → independent review → `reviewed-pass` → merge → the planner
> moves it to `../memory/completed-tasks.md` (`✅`). Here workers are Opus sub-agents dispatched by the
> Fable planner session, so `session:` is the sub-agent run, not a separate session id.

## Queue
*(stable `#N` IDs — never renumber. Every slice → plan: `planning/plans/stock-researcher-v1.md` (slice: S<N>).)*
- ⏳ **#1** S1 Data layer — provider Protocol + yfinance provider + captured fixtures (AAPL, sparse, negative-EPS, unknown) + FakeProvider/no-network guard + snapshot/normalize + technicals + `snapshot` CLI · **owner:** unassigned · branch `s1-data-layer`
- ⏳ **#2** S2 Scoring — scorecard + fair value + labels L1-L8 + `score` CLI · **owner:** unassigned · branch `s2-scoring` · ⚠ scoring math = data-fidelity trigger → recommend `/code-review ultra` before merge
- ⏳ **#3** S3 Output — report skeleton + `assemble` + front-matter + derived ledger + `run` CLI + docs (scorecard/fair-value/labels/README) · **owner:** unassigned · branch `s3-output`
- ⏳ **#4** S4 Agents + command — five Opus agent files + shared contract + `.claude/commands/research.md`; first live `/research AAPL` · **owner:** unassigned · branch `s4-agents`
- ⏳ **#5** S5 Guards — `verify-citations`, bear-case agent, provider retry/backoff, `--offline`, `test_live.py` · **owner:** unassigned · branch `s5-guards`
- ⏳ **#6** S6 Resume polish — sample report committed, README walkthrough, console score table · **owner:** unassigned · branch `s6-polish`

## Deferred (phase 3, not planned in detail)
- Paid provider (FMP / Polygon) behind the same Protocol · batch mode · dashboard.

✅ Completed → `../memory/completed-tasks.md` (the planner moves merged tasks there on merge).
