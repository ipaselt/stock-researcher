# `/research <TICKER>` — command body (planner-authored; S4 copies this into `.claude/commands/research.md`)

> Status: approved v1, 2026-09-28. The command is executed by the planner session (Fable). Every heavy step
> is a Python call or an Opus sub-agent; Fable reads small JSON and writes ~150 words.

## Frontmatter
```yaml
---
description: Research and rate one US-listed stock — snapshot, scorecard, five Opus analysts, planner verdict, report, ledger
argument-hint: [TICKER]
disable-model-invocation: true
allowed-tools: Bash(.venv/Scripts/python.exe -m stock_researcher:*), Bash(git add:*), Bash(git commit:*), Bash(git rev-parse:*), Read, Write, Agent
---
```

## Body

You are running one research pass on `$ARGUMENTS` for this desk. Work from the repo root
(`git rev-parse --show-toplevel`); the Python is `.venv/Scripts/python.exe`. Follow the steps in order; do not
skip the citation check; do not write more than the verdict file yourself.

1. **Validate.** `$ARGUMENTS` must be 1-6 letters/dots/hyphens. Upper-case it as `T`. If empty, stop and ask for a ticker.
2. **Data + score.** Run `.venv/Scripts/python.exe -m stock_researcher run T`. Exit 2 → report the message and stop
   (unknown ticker, reserved name, or data unreadable). It writes `data/T.json`, `data/T.score.json`,
   `data/T/skeleton.md`.
3. **Read the score.** Read `data/T.score.json` and note: `total`, `band_word`, `coverage_pct`,
   `label_suggestion` (label, rule_id, reason, entry_target), `fair_value` (fair_value, band_high, entry_price,
   fair_pe_source, reason). Do not read the whole snapshot.
4. **Fan out the five analysts in ONE message** — `valuation`, `growth-quality`, `balance-sheet-risk`,
   `technicals`, `news-catalysts` (five parallel `Agent` calls, `subagent_type` = the agent name,
   run in the background). Each dispatch message contains: the ticker, the absolute paths of `data/T.json` and
   `data/T.score.json`, the sections that agent reads (from its Focus block), and its output path
   `data/T/<agent>.md`. Wait for all five.
5. **Citation check.** Run `.venv/Scripts/python.exe -m stock_researcher verify-citations T`. For each agent it
   reports as FAIL (a cited number absent from the JSON or off by more than 1%), re-dispatch that agent once with
   the failure lines quoted; if it fails again, overwrite its file with empty content using Write (an empty agent file counts as "did not report").
   The appendix of the assembled report shows the result.
6. **Bear case (optional).** If the suggested label is BUY or the owner asked for it, dispatch `bear-case` with the
   snapshot path, the absolute path of `data/T.score.json`, the suggested label + rule id, and the five agent
   files; wait.
7. **Verdict.** Read the five (six) agent files' `### Assessment` paragraphs and JSON blocks — nothing more. Write
   `data/T/verdict.md`:
   ```
   ---
   label_final: <BUY | SELL | WAIT | HAS RUN | NOT LOOKING>
   entry_target: <number | none>
   override_reason: <none | "L<n> suggested X; overriding to Y because <one sentence citing a snapshot number or an agent finding>">
   ---
   ### Thesis
   ≤ 150 words: what this company is, why the label, at what price.
   ### Key risks
   - three bullets, each citing a number or an agent flag
   ### What changes my mind
   - two bullets: the observation that would flip the label
   ### Triggers
   - what to watch and when (next earnings date if present)
   ```
   Confirm the suggested label unless an agent finding or a data gap gives a specific, cited reason to override.
   `entry_target` = the score's `entry_price` for WAIT / HAS RUN / BUY, else `none`. If the suggested rule was L5 (no
   fair value) and you override to WAIT or BUY, `entry_target` is `none` (never `null`) unless you cite a price
   from an agent finding.
8. **Assemble.** `.venv/Scripts/python.exe -m stock_researcher assemble T` → `reports/T-<date>.md` and the rebuilt
   `reports/ratings.csv`.
9. **Commit the report** (markdown only): `git add reports/T-<date>.md && git commit -m "research: T <label_final> (<date>)" -- reports/T-<date>.md`
   (pathspec-scoped so nothing else already staged rides along).
   Do not commit `data/` or `ratings.csv` (both are regenerated).
10. **Summarize in five lines:** label (and whether it overrode the rule), score + band + coverage, fair value + entry
    target, the one-sentence thesis, the report path.
