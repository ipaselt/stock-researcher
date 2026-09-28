# Lessons — stock-researcher (in-repo durable record)

> Project-specific lessons — the version-controlled subset distilled from this project's **native
> auto-memory** by `/wrap`; `/groom` consolidates. Keep it lean, one fact per entry, pointers not
> re-explanations. Cross-project orchestration wisdom lives in `~/Developer/memory/lessons.md`; truly
> universal lessons graduate up into `~/.claude/rules/`.

- yfinance units are mixed per field (percent vs fraction) — normalize in one table with explicit codes and
  regression-test each scale; never hand-format elsewhere (inherited from portfolio-lab, re-verified 2026-09-28).
- Only the cwd's `.claude/` loads — project agents and commands must live inside the project, not at the dev root.
