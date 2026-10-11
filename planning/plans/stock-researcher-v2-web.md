# Plan v2 — stock-researcher web (publish the reports on Vercel)

> Status: **approved** · Created 2026-09-28 · Slice S11 (`web/`) → `planning/todo.md` #11.

## Context
Plan v1 (below, complete 2026-09-28) built the research engine and produced two committed reports. The owner now
wants a public website so the research is visible without opening the repo — a resume-facing showcase. Decisions
locked with the owner (2026-09-28):
| Decision | Choice |
|---|---|
| Scope | Publish the committed reports and the ratings ledger; research keeps running in Claude Code; each research commit auto-deploys. No live scoring, no agents on the site. |
| Stack | Next.js App Router (static generation from `reports/*.md` at build time), Tailwind |
| Location | `web/` folder in the same repo; Vercel Root Directory = `web` |
| Hosting | Vercel Hobby (free) at `<project>.vercel.app`; the owner logs in (`vercel login`) — I cannot |

## Facts that shape the design (verified by exploration)
- `reports/ratings.csv` is **gitignored** → the site builds its index from each report's front-matter.
- Front-matter is flat, written by `stock_researcher/report.py` (`front_matter` / `parse_front_matter`, lines ~86-126):
  split each line on the FIRST `:`; a `"…"` value is JSON (used for `override_reason`, which can contain colons and
  semicolons); `none` / `"none"` mean null; every value is a string. A YAML library would mangle this → hand-rolled parser.
- Report body: `# TICKER — Name`, then `##` sections; each agent section repeats a nested H2 ending in ` — TICKER` and
  ends with a ```json block (sometimes one very long line); appendix links point at `../docs/<name>.md`.
- job-tailor conventions to copy: Next 16.2.12 / React 19.2.4 / Tailwind v4 CSS-first / TS strict / `src/` + `@/*` /
  Geist fonts / eslint flat config. Port 3000 is taken → 3001. Node 24.14.1 locally.
- Vercel: Git-integration deploy with Root Directory `web`; the build clones the whole repo so `../reports` and
  `../docs` are readable ("Include source files outside of the Root Directory" must stay ON). Manual CLI deploys must be
  linked at the REPO ROOT (a `vercel` upload from `web/` would not carry `../reports`).
- `/research` step 9 commits the report but does not push → auto-deploy needs a push (fixed in this slice).

## Design (one Opus worker PR, slice **S11 web**, branch `s11-web`)
```
web/
  package.json · package-lock.json · next.config.ts (default) · postcss.config.mjs · tsconfig.json · eslint.config.mjs · vitest.config.ts
  src/app/globals.css        @import tailwindcss; @plugin typography; tokens + dark block (job-tailor shape)
  src/app/layout.tsx         Geist fonts, <Nav/>, <main max-w-5xl>, footer with the disclaimer + GitHub link, title template
  src/app/page.tsx           dashboard: "N reports · latest <date>" + <ReportTable/>
  src/app/not-found.tsx
  src/app/reports/[slug]/page.tsx        generateStaticParams + dynamicParams=false + generateMetadata; verdict card; jump bar; body
  src/app/reports/[slug]/opengraph-image.tsx   OPTIONAL (≤ ~25 lines via next/og; keep only if the build lists it static)
  src/app/methodology/[doc]/page.tsx     scorecard / fair-value / labels (allowlist) + sub-nav
  src/components/nav.tsx ("use client") · chips.tsx (LabelChip, GradeChip, band(), fmtMoney/fmtPct) · report-table.tsx ("use client", useState label filter) · markdown.tsx
  src/lib/frontmatter.ts     parseFrontMatter — parity with report.py (first colon, JSON unquote w/ fallback, 'x' strip, none→null, malformed→null, CRLF ok)
  src/lib/reports.ts         repoRoot() (walk up ≤4 dirs until reports/ + docs/ exist, else throw a loud message), ReportMeta, listReports(dir?), getReport(slug) (SLUG_RE guard), cleanBody (drop H1 + `## … — TICKER`), listDocs/getDoc (allowlist), firstSentence()
  src/lib/*.test.ts + test/fixtures/reports/{AAA,BBB}-*.md   (vitest: parser round-trips the quoted reason; listing sorts newest first; none→null; nested H2 dropped)
```
- **Rendering:** `react-markdown@^10` + `remark-gfm@^4` (no `rehype-raw` → no HTML injection; no MDX; no yaml lib).
  Component map: `table` → `overflow-x-auto` + `tabular-nums`; `td` plain-string `A-F` → GradeChip, label words → LabelChip;
  `pre` with `language-json` → collapsed `<details>` "Analyst JSON summary"; `a` `../docs/<n>.md` → `/methodology/<n>`,
  external → new tab; `h2` gets `id=slug(text)` (own 1-line slug, shared with the jump bar).
- **Static guarantee:** both dynamic routes use `generateStaticParams` + `dynamicParams = false`; no `searchParams` /
  `headers` / `cookies`; the filter is client `useState` on serialised props; `fs` code is never imported by a client file.
  Build must show `●` for `/reports/[slug]` ×2 and `/methodology/[doc]` ×3, `○` for `/`, no `ƒ` routes.
- **Styling:** Tailwind v4; label colours BUY emerald · WAIT amber · HAS RUN sky · SELL rose · NOT LOOKING zinc; grades
  A emerald · B lime · C amber · D orange · F rose; `prose` from typography; mobile-first; no component library.
- **Tooling:** scripts `dev -p 3001` · `build` · `start` · `lint` · `test` (vitest ^5, needs Node ≥22.12 — we have 24);
  deps pinned to job-tailor's versions except `@types/node ^24`. Root `.gitignore` += `.vercel/`, `next-env.d.ts`,
  `*.tsbuildinfo`. Root `README.md` gains a "Website" section. New `.claude/launch.json` at the repo root:
  `stock-researcher-web` → `npm --prefix web run dev`, port 3001.
- **Research command:** `.claude/commands/research.md` step 9 adds `git push origin main` after the report commit
  (+ `Bash(git push:*)` in allowed-tools; the planning spec mirrors it) so a finished report deploys itself.

## Vercel (owner steps; nothing needs env vars)
1. `vercel login` once (browser). 2. vercel.com → Add New → Project → Import `ipaselt/stock-researcher`.
3. Root Directory **`web`**; keep "Include source files outside of the Root Directory" **ON**; framework auto = Next.js. Deploy.
4. Settings → Git: production branch `main`. If a `reports/`-only push ever shows "skipped", set Ignored Build Step to
   `git diff --quiet HEAD^ HEAD -- web reports docs`.
CLI alternative: from the REPO ROOT `vercel link` then `vercel git connect`, then set Root Directory in the dashboard.

## Verification
- Worker: `npm run lint`, `npm run test` (2 files green), `npm run build` (route table as above; `ls .next/server/app/reports/*.html` → 2 files), `cd .. && npm --prefix web run build` (cwd robustness).
- Planner: adversarial review (focus: `repoRoot()` on Vercel `/vercel/path0/web` vs local; parser parity with Python;
  XSS surface; static guarantees; client/server import boundary), then the in-app preview on port 3001: `/` shows 2 rows,
  NVDA row WAIT with "was BUY", the WAIT filter hides AAPL; `/reports/NVDA-2026-09-28` shows the override note, grade
  chips, six collapsed JSON blocks, one `## Valuation`, methodology links → `/methodology/...`; `/methodology/scorecard`
  renders the band table; `/reports/nope` → 404. Then merge, owner imports on Vercel, I check the live URL.

## Risks
Format drift in a future report breaks the build (parser returns null + skip-and-warn; nullable meta; tests pin the
contract; the only hard failure is `repoRoot()`, on purpose) · Vercel outside-files toggle off (loud error) · monorepo
skip on report-only pushes (Ignored Build Step fallback) · Vitest 5 Node floor (24 locally; Vercel default Node is fine).
