import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Stock Researcher", template: "%s · Stock Researcher" },
  description:
    "Research reports on US-listed stocks: a deterministic scorecard, fair value and entry price, and an analyst verdict.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col font-sans">
        <Nav />
        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
          {children}
        </main>
        <footer className="border-t border-black/[.08] dark:border-white/[.12]">
          <div className="mx-auto flex max-w-5xl flex-col gap-1 px-6 py-4 text-xs text-zinc-500 sm:flex-row sm:justify-between dark:text-zinc-400">
            <p>This is generated research for the owner&apos;s own process. It is not investment advice.</p>
            <a
              href="https://github.com/ipaselt/stock-researcher"
              target="_blank"
              rel="noreferrer"
              className="hover:text-black dark:hover:text-white"
            >
              Source on GitHub
            </a>
          </div>
        </footer>
      </body>
    </html>
  );
}
