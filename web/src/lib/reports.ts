import fs from "node:fs";
import path from "node:path";
import { cache } from "react";
import { parseFrontMatter } from "./frontmatter";

// Reads the committed reports/ and docs/ at build time. Server-only (node:fs); client files import types only.

export function repoRoot(): string {
  const start = process.cwd();
  let dir = start;
  for (let i = 0; i <= 4; i++) {
    if (fs.existsSync(path.join(dir, "reports")) && fs.existsSync(path.join(dir, "docs"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  throw new Error(
    `reports/ and docs/ not found above ${start} — on Vercel, is "Include source files outside of the Root Directory" on?`,
  );
}

export const REPORTS_DIR = () => path.join(repoRoot(), "reports");
export const DOCS_DIR = () => path.join(repoRoot(), "docs");

// TICKER-YYYY-MM-DD; also the path-traversal guard for slugs.
export const SLUG_RE = /^([A-Z][A-Z0-9.\-]*)-(\d{4}-\d{2}-\d{2})$/;

export type Label = "BUY" | "WAIT" | "HAS RUN" | "SELL" | "NOT LOOKING";

export type ReportMeta = {
  slug: string;
  ticker: string;
  name: string;
  date: string;
  price: number | null;
  score: number | null;
  coverage: number | null;
  fairValue: number | null;
  entry: number | null;
  labelSuggested: string | null;
  ruleId: string | null;
  labelFinal: string;
  overrideReason: string | null;
  thesis: string;
};

export type Section = { text: string; id: string };
export type Report = { meta: ReportMeta; body: string; sections: Section[] };

/** Heading anchor id; the markdown renderer uses the same function for its `<h2 id>`. */
export function slug(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function num(v: string | null | undefined): number | null {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Drop the H1 and the agents' own `## <Title> — TICKER` lines (the report already has a section H2). */
export function cleanBody(body: string, ticker: string): string {
  const nested = new RegExp(`^## .+ — ${escapeRe(ticker)}\\s*$`);
  return body
    .split(/\r?\n/)
    .filter((line) => !line.startsWith("# ") && !nested.test(line))
    .join("\n");
}

function sectionsOf(body: string): Section[] {
  const out: Section[] = [];
  let fenced = false;
  for (const line of body.split("\n")) {
    if (line.startsWith("```")) fenced = !fenced;
    else if (!fenced && line.startsWith("## ")) {
      const text = line.slice(3).trim();
      out.push({ text, id: slug(text) });
    }
  }
  return out;
}

function thesisOf(body: string): string {
  const paras = body.split(/\r?\n\s*\r?\n/).map((p) => p.trim());
  const i = paras.findIndex((p) => p.startsWith("**Final label:"));
  return i >= 0 && i + 1 < paras.length ? paras[i + 1] : "";
}

/** Parse one report's text; null when the slug or the front-matter is invalid. */
export function parseReport(slugText: string, text: string): Report | null {
  const m = SLUG_RE.exec(slugText);
  const parsed = parseFrontMatter(text);
  if (!m || !parsed) return null;
  const f = parsed.fields;
  const ticker = f.ticker ?? m[1];
  const name = new RegExp(`^# ${escapeRe(ticker)} — (.+)$`, "m").exec(parsed.body)?.[1].trim() ?? ticker;
  const labelSuggested = f.label_suggested ?? null;
  const body = cleanBody(parsed.body, ticker);
  const meta: ReportMeta = {
    slug: slugText,
    ticker,
    name,
    date: f.date ?? m[2],
    price: num(f.price),
    score: num(f.score),
    coverage: num(f.coverage),
    fairValue: num(f.fair_value),
    entry: num(f.entry),
    labelSuggested,
    ruleId: f.rule_id ?? null,
    labelFinal: f.label_final ?? labelSuggested ?? "?",
    overrideReason: f.override_reason ?? null,
    thesis: thesisOf(parsed.body),
  };
  return { meta, body, sections: sectionsOf(body) };
}

export function listReports(dir: string = REPORTS_DIR()): ReportMeta[] {
  const metas: ReportMeta[] = [];
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith(".md")) continue;
    const stem = file.slice(0, -3);
    if (!SLUG_RE.test(stem)) continue;
    const report = parseReport(stem, fs.readFileSync(path.join(dir, file), "utf-8"));
    if (!report) {
      console.warn(`skipping ${file}: unreadable front-matter`);
      continue;
    }
    metas.push(report.meta);
  }
  return metas.sort((a, b) =>
    a.date === b.date ? a.ticker.localeCompare(b.ticker) : a.date < b.date ? 1 : -1,
  );
}

export const getReport = cache((slugText: string): Report | null => {
  if (!SLUG_RE.test(slugText)) return null;
  const file = path.join(REPORTS_DIR(), `${slugText}.md`);
  if (!fs.existsSync(file)) return null;
  return parseReport(slugText, fs.readFileSync(file, "utf-8"));
});

export const DOCS = [
  { name: "scorecard", title: "Scorecard" },
  { name: "fair-value", title: "Fair value" },
  { name: "labels", title: "Labels" },
] as const;

export type Doc = { name: string; title: string; body: string };

export function listDocs() {
  return DOCS;
}

export function getDoc(name: string): Doc | null {
  const entry = DOCS.find((d) => d.name === name);
  if (!entry) return null;
  const body = fs.readFileSync(path.join(DOCS_DIR(), `${entry.name}.md`), "utf-8");
  const title = /^# (.+)$/m.exec(body)?.[1].trim() ?? entry.title;
  return { name: entry.name, title, body };
}

export function firstSentence(text: string): string {
  const first = text.split(/\.\s/)[0].trim();
  const sentence = first.endsWith(".") ? first : `${first}.`;
  return sentence.length > 160 ? `${sentence.slice(0, 159).trimEnd()}…` : sentence;
}
