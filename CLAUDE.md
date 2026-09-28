# CLAUDE.md — stock-researcher

A stock research and rating engine for US-listed common stocks, built like a small research firm: a
deterministic Python core (data → normalized snapshot → weighted scorecard → fair value / entry price →
suggested label) plus a Claude Code `/research <TICKER>` command that fans out to Opus research agents
and lets the planner (Fable) write the verdict. Output: one markdown report per ticker. Home base:
`projects/stock-researcher/` (the repo root = the main-branch checkout).

> Auto-loads when an agent works in this project. Apply the method in
> `~/Developer/guide-setup/method/KORTANNA-METHOD.md`; stamp from `…/method/templates/`.

## Workspace Map
```
stock-researcher/                — THE git repo (this folder = the main-branch checkout)
├── CLAUDE.md      — this file (identity + map + routing) · CONTEXT.md — worker dispatcher
├── .orchestrated  — marker: main is merge-only (activates the main-protection hook)
├── planning/      — todo.md (⏳ slices · planner-owned) · progress.md (🔄 board) · plans/ (approved plans)
├── memory/        — primer.md (state) · decisions.md (append-only) · completed-tasks.md (✅) · lessons.md
├── docs/          — scorecard.md · fair-value.md · labels.md — the methodology (docs = code, test-enforced)
├── .claude/       — commands/research.md (the /research flow) · agents/*.md (Opus research agents)
├── stock_researcher/ — the package: providers/ · snapshot · normalize · technicals · scorecard · fair_value
│                    · labels · report · ledger · citations · cli
├── tests/         — pytest, zero network by default (FakeProvider + fixtures/); `-m live` for the canary
├── data/          — gitignored run artifacts: <T>.json · <T>.score.json · <T>/<agent>.md · <T>/verdict.md
├── reports/       — <T>-<YYYY-MM-DD>.md (committed; YAML front-matter = ledger source) · ratings.csv (derived)
└── branches/<task>/ — gitignored per-task worktrees; code work happens here
```
Use this tree to locate files directly — don't Glob/LS the root to discover structure.

## Stack · Routing · Commands
- **Stack:** Python 3.11 · `yfinance==1.5.1` (behind `providers/base.py`, swappable for a paid API later)
  · `pandas` · `pytest` · Claude Code agents/commands (Opus workers, Fable planner).
- **Routing:** data fetch → `stock_researcher/providers/` · unit rules → `normalize.py` (the ONLY place
  yfinance keys appear outside the provider) · scoring math → `scorecard.py` / `fair_value.py` / `labels.py`
  · report text → `report.py` · the research flow → `.claude/commands/research.md` · agent behaviour →
  `.claude/agents/<name>.md` · methodology prose → `docs/`. `CONTEXT.md` routes one level deeper.
- **Commands:** `.venv/Scripts/python.exe -m stock_researcher run <TICKER>` (snapshot + score + skeleton)
  · `/research <TICKER>` (full flow, run by the planner) · `pytest` (test) · `pytest -m live` (network canary).

## Validation
Run before reporting work complete. Only passing output should reach the user.
```bash
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m stock_researcher --help
```

## Project-Specific Rules
- **Units:** every stored ratio is a fraction or a multiple, never a percent. yfinance's `dividendYield` and
  `debtToEquity` arrive as percents and are divided by 100 in `normalize.py`; margins/growth/ROE arrive as
  fractions. Each field carries an explicit unit code and a regression test. Never hand-format units elsewhere.
- **Research agents cite, never compute.** An agent may only state numbers present in `data/<T>.json` /
  `data/<T>.score.json`, with the key in parentheses. `verify-citations` enforces it; a failing agent is re-run
  or dropped, never patched by hand.
- **Deterministic first, judgment second.** The scorecard and label rule (L1-L8) are code and documented in
  `docs/`; Fable may override a label only with the rule id, the new label, and one cited reason.
- **Zero network in tests** (autouse guard). Fixtures are captured once and committed; `test_live.py` is the
  only thing that touches Yahoo.
- **Reports are the ledger source.** `reports/ratings.csv` is regenerated from report front-matter; never
  edit it by hand.
- Not investment advice: every report carries the disclaimer line.

## Conventions
- Spec before code; one fact, one location; lowercase-hyphen naming; `pathlib` + `encoding="utf-8"` everywhere.
- Secrets (a future paid data API key) in `.env` (gitignored). Never hardcode.
- Planner (Fable) writes `.md` only and dispatches; Opus workers write code in `branches/<task>/` → PR →
  independent review → `reviewed-pass` → merge. Scoring-math slices get flagged for `/code-review ultra`.

## Current State
- 2026-09-28: plan v1 complete — S0-S6 merged (full `/research` flow + citation guard, 583 tests); sample report `reports/AAPL-2026-09-28.md` citation-verified.
- Next: backlog `planning/todo.md` #7-#9 (guard follow-ups, more tickers from an in-project session). Status home: `memory/primer.md` (current) + `planning/progress.md` (in-flight).

## Key Decisions (ADRs)
- Separate repo from `portfolio-lab` — that one is a holdings tracker; this is a rating engine. Lessons reused, code not.
- yfinance behind a provider Protocol — free now, paid API later without touching scoring.
- Hybrid rating (scorecard + Fable verdict) — reproducible and interview-defensible, with judgment on top.
- Single Fable session + Opus sub-agents, not multi-session — the lightest orchestration rung that fits.
- Full log: `memory/decisions.md`.

## Avoid
- No trade execution, no broker connection, ever — research only.
- No abstraction beyond the provider Protocol; no config framework; no database.
- Never commit `data/`, `.env`, or a hand-edited `ratings.csv`.
- Writing behavioral rules here — they belong in the rules system or the worker role prompt.
