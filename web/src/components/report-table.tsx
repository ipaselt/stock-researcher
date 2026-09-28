"use client";

import Link from "next/link";
import { useState } from "react";
import { LABELS, LabelChip, band, fmtMoney, fmtPct } from "@/components/chips";
import type { Label, ReportMeta } from "@/lib/reports";

const PILL = "rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition-colors";
const PILL_ON = "bg-black text-white ring-black dark:bg-white dark:text-black dark:ring-white";
const PILL_OFF =
  "text-zinc-600 ring-zinc-200 hover:bg-black/[.04] dark:text-zinc-400 dark:ring-zinc-800 dark:hover:bg-white/[.06]";

export function ReportTable({ reports }: { reports: ReportMeta[] }) {
  const [filter, setFilter] = useState<Label | "ALL">("ALL");
  const counts = new Map<string, number>();
  for (const r of reports) counts.set(r.labelFinal, (counts.get(r.labelFinal) ?? 0) + 1);
  const present = LABELS.filter((l) => counts.has(l)) as Label[];
  const shown = filter === "ALL" ? reports : reports.filter((r) => r.labelFinal === filter);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {(["ALL", ...present] as const).map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setFilter(l)}
            className={`${PILL} ${filter === l ? PILL_ON : PILL_OFF}`}
          >
            {l === "ALL" ? "All" : l} {l === "ALL" ? reports.length : counts.get(l)}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm tabular-nums">
          <thead className="border-b border-zinc-200 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            <tr>
              <th className="py-2 pr-4 font-medium">Ticker</th>
              <th className="py-2 pr-4 font-medium">Label</th>
              <th className="py-2 pr-4 font-medium">Score</th>
              <th className="py-2 pr-4 font-medium">Coverage</th>
              <th className="hidden py-2 pr-4 font-medium sm:table-cell">Fair value</th>
              <th className="py-2 pr-4 font-medium">Entry</th>
              <th className="py-2 font-medium">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
            {shown.map((r) => (
              <tr key={r.slug} className="align-top">
                <td className="py-3 pr-4">
                  <Link href={`/reports/${r.slug}`} className="group block">
                    <span className="font-semibold group-hover:underline">{r.ticker}</span>
                    <span className="block text-xs text-zinc-500 dark:text-zinc-400">{r.name}</span>
                  </Link>
                </td>
                <td className="py-3 pr-4">
                  <LabelChip label={r.labelFinal} />
                  {r.labelSuggested && r.labelSuggested !== r.labelFinal && (
                    <span className="mt-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      was {r.labelSuggested}
                    </span>
                  )}
                </td>
                <td className="py-3 pr-4">
                  {r.score == null ? (
                    "—"
                  ) : (
                    <>
                      {r.score.toFixed(1)}{" "}
                      <span className="text-xs text-zinc-500 dark:text-zinc-400">{band(r.score)}</span>
                    </>
                  )}
                </td>
                <td className="py-3 pr-4">{fmtPct(r.coverage)}</td>
                <td className="hidden py-3 pr-4 sm:table-cell">{fmtMoney(r.fairValue)}</td>
                <td className="py-3 pr-4">{fmtMoney(r.entry)}</td>
                <td className="py-3 whitespace-nowrap">{r.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
