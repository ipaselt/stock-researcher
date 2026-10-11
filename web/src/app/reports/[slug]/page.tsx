import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { LabelChip, band, fmtMoney, fmtPct } from "@/components/chips";
import { Markdown } from "@/components/markdown";
import { firstSentence, getReport, listReports } from "@/lib/reports";

export const dynamicParams = false;

export function generateStaticParams() {
  return listReports().map((r) => ({ slug: r.slug }));
}

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const report = getReport((await params).slug);
  if (!report) return {};
  const { ticker, labelFinal, date, thesis } = report.meta;
  const title = `${ticker} — ${labelFinal} — ${date}`;
  const description = firstSentence(thesis);
  return { title, description, openGraph: { title, description } };
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500 dark:text-zinc-400">{label}</div>
      <div className="mt-0.5 font-medium tabular-nums">{value}</div>
    </div>
  );
}

export default async function ReportPage({ params }: Props) {
  const report = getReport((await params).slug);
  if (!report) notFound();
  const { meta, body, sections } = report;
  const overridden = meta.labelSuggested != null && meta.labelSuggested !== meta.labelFinal;
  const rule = `${meta.labelSuggested ?? "?"}${meta.ruleId ? ` (${meta.ruleId})` : ""}`;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {meta.ticker} <span className="font-normal text-zinc-500 dark:text-zinc-400">{meta.name}</span>
            </h1>
            <p className="mt-1 text-sm text-zinc-600 tabular-nums dark:text-zinc-400">
              {meta.date} · {fmtMoney(meta.price)}
            </p>
          </div>
          <LabelChip label={meta.labelFinal} className="px-3 py-1 text-base" />
        </div>
        <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Score"
            value={meta.score == null ? "—" : `${meta.score.toFixed(1)} / 100 · ${band(meta.score)}`}
          />
          <Stat label="Coverage" value={fmtPct(meta.coverage)} />
          <Stat label="Fair value" value={fmtMoney(meta.fairValue)} />
          <Stat label="Entry" value={fmtMoney(meta.entry)} />
        </div>
        {overridden ? (
          <p className="mt-5 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
            Overrides the rule&apos;s {rule}: {meta.overrideReason ?? "no reason recorded."}
          </p>
        ) : (
          <p className="mt-5 text-sm text-zinc-600 dark:text-zinc-400">Confirms the rule&apos;s {rule}.</p>
        )}
      </section>

      <nav className="flex flex-wrap gap-x-4 gap-y-1 border-b border-zinc-200 pb-3 text-sm dark:border-zinc-800">
        {sections.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="text-zinc-600 hover:text-black dark:text-zinc-400 dark:hover:text-white"
          >
            {s.text}
          </a>
        ))}
      </nav>

      <Markdown body={body} />
    </div>
  );
}
