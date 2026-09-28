// Pure presentational helpers: no hooks, no fs — usable from server and client components.

const CHIP = "inline-flex rounded-md px-2 py-0.5 text-xs font-semibold ring-1 ring-inset";

export const LABEL_STYLE: Record<string, string> = {
  BUY: "bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-900",
  WAIT: "bg-amber-100 text-amber-800 ring-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-900",
  "HAS RUN": "bg-sky-100 text-sky-800 ring-sky-200 dark:bg-sky-950 dark:text-sky-300 dark:ring-sky-900",
  SELL: "bg-rose-100 text-rose-800 ring-rose-200 dark:bg-rose-950 dark:text-rose-300 dark:ring-rose-900",
  "NOT LOOKING": "bg-zinc-100 text-zinc-800 ring-zinc-200 dark:bg-zinc-950 dark:text-zinc-300 dark:ring-zinc-900",
};

export const GRADE_STYLE: Record<string, string> = {
  A: "bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-900",
  B: "bg-lime-100 text-lime-800 ring-lime-200 dark:bg-lime-950 dark:text-lime-300 dark:ring-lime-900",
  C: "bg-amber-100 text-amber-800 ring-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-900",
  D: "bg-orange-100 text-orange-800 ring-orange-200 dark:bg-orange-950 dark:text-orange-300 dark:ring-orange-900",
  F: "bg-rose-100 text-rose-800 ring-rose-200 dark:bg-rose-950 dark:text-rose-300 dark:ring-rose-900",
  "—": "bg-zinc-100 text-zinc-800 ring-zinc-200 dark:bg-zinc-950 dark:text-zinc-300 dark:ring-zinc-900",
};

export const LABELS = Object.keys(LABEL_STYLE);

export function LabelChip({ label, className = "" }: { label: string; className?: string }) {
  return (
    <span className={`${CHIP} whitespace-nowrap ${LABEL_STYLE[label] ?? LABEL_STYLE["NOT LOOKING"]} ${className}`}>
      {label}
    </span>
  );
}

export function GradeChip({ grade }: { grade: string }) {
  return <span className={`${CHIP} ${GRADE_STYLE[grade] ?? GRADE_STYLE["—"]}`}>{grade}</span>;
}

export function band(score: number): string {
  if (score >= 75) return "strong";
  if (score >= 60) return "good";
  if (score >= 45) return "mixed";
  return "weak";
}

const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function fmtMoney(v: number | null): string {
  return v == null ? "—" : USD.format(v);
}

export function fmtPct(c: number | null): string {
  return c == null ? "—" : `${Math.round(c * 100)}%`;
}
