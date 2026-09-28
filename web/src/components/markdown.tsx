import Link from "next/link";
import { isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { GradeChip, LabelChip } from "@/components/chips";
import { slug } from "@/lib/reports";

export { slug };

const LABEL_CELL = /^(BUY|WAIT|HAS RUN|SELL|NOT LOOKING)\b([\s\S]*)$/;

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children);
  return "";
}

const components: Components = {
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto">
      <table {...props} className="tabular-nums" />
    </div>
  ),
  td: ({ node, children, ...props }) => {
    if (typeof children === "string") {
      if (/^[A-F]$/.test(children)) {
        return (
          <td {...props}>
            <GradeChip grade={children} />
          </td>
        );
      }
      const m = LABEL_CELL.exec(children);
      if (m) {
        return (
          <td {...props}>
            <LabelChip label={m[1]} />
            {m[2]}
          </td>
        );
      }
    }
    return <td {...props}>{children}</td>;
  },
  pre: ({ node, children, ...props }) => {
    const lang = isValidElement<{ className?: string }>(children) ? children.props.className ?? "" : "";
    if (lang.includes("language-json")) {
      return (
        <details className="not-prose my-4 rounded-md border border-zinc-200 dark:border-zinc-800">
          <summary className="cursor-pointer px-3 py-2 text-sm">Analyst JSON summary</summary>
          <pre className="overflow-x-auto p-3 text-xs">{children}</pre>
        </details>
      );
    }
    return (
      <pre {...props} className="overflow-x-auto">
        {children}
      </pre>
    );
  },
  a: ({ node, href = "", children, ...props }) => {
    const doc = /^\.\.\/docs\/([a-z-]+)\.md$/.exec(href);
    if (doc) return <Link href={`/methodology/${doc[1]}`}>{children}</Link>;
    if (/^https?:\/\//.test(href)) {
      return (
        <a {...props} href={href} target="_blank" rel="noreferrer">
          {children}
        </a>
      );
    }
    return <Link href={href}>{children}</Link>;
  },
  h2: ({ node, children, ...props }) => (
    <h2 {...props} id={slug(textOf(children))}>
      {children}
    </h2>
  ),
};

export function Markdown({ body }: { body: string }) {
  return (
    <article className="prose prose-zinc dark:prose-invert max-w-none prose-headings:scroll-mt-24 prose-table:text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {body}
      </ReactMarkdown>
    </article>
  );
}
