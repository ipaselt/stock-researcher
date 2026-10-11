import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Not found</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">There is no report or page at this address.</p>
      <Link href="/" className="mt-6 inline-block text-sm font-medium underline underline-offset-4">
        All reports
      </Link>
    </div>
  );
}
