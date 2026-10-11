"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const IDLE =
  "text-zinc-600 hover:bg-black/[.04] hover:text-black dark:text-zinc-400 dark:hover:bg-white/[.06] dark:hover:text-white";
const ACTIVE = "bg-black/[.06] font-medium text-black dark:bg-white/[.12] dark:text-white";

export function Nav() {
  const pathname = usePathname();
  const links = [
    { href: "/", label: "Reports", active: pathname === "/" || pathname.startsWith("/reports") },
    { href: "/methodology/scorecard", label: "Methodology", active: pathname.startsWith("/methodology") },
  ];
  return (
    <header className="border-b border-black/[.08] dark:border-white/[.12]">
      <nav className="mx-auto flex max-w-5xl items-center gap-1 px-6 py-3">
        <Link href="/" className="mr-4 font-semibold tracking-tight">
          Stock&nbsp;Researcher
        </Link>
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded-md px-3 py-1.5 text-sm transition-colors ${l.active ? ACTIVE : IDLE}`}
          >
            {l.label}
          </Link>
        ))}
        <a
          href="https://github.com/ipaselt/stock-researcher"
          target="_blank"
          rel="noreferrer"
          className={`ml-auto rounded-md px-3 py-1.5 text-sm transition-colors ${IDLE}`}
        >
          GitHub
        </a>
      </nav>
    </header>
  );
}
