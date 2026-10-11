import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Markdown } from "@/components/markdown";
import { DOCS, getDoc } from "@/lib/reports";

export const dynamicParams = false;

export function generateStaticParams() {
  return DOCS.map((d) => ({ doc: d.name }));
}

type Props = { params: Promise<{ doc: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const doc = getDoc((await params).doc);
  return doc ? { title: `${doc.title} · Methodology` } : {};
}

export default async function MethodologyPage({ params }: Props) {
  const doc = getDoc((await params).doc);
  if (!doc) notFound();
  return (
    <div className="space-y-6">
      <nav className="flex flex-wrap gap-1 border-b border-zinc-200 pb-3 dark:border-zinc-800">
        {DOCS.map((d) => (
          <Link
            key={d.name}
            href={`/methodology/${d.name}`}
            className={`rounded-md px-3 py-1.5 text-sm ${
              d.name === doc.name
                ? "bg-black/[.06] font-medium text-black dark:bg-white/[.12] dark:text-white"
                : "text-zinc-600 hover:text-black dark:text-zinc-400 dark:hover:text-white"
            }`}
          >
            {d.title}
          </Link>
        ))}
      </nav>
      <Markdown body={doc.body} />
    </div>
  );
}
