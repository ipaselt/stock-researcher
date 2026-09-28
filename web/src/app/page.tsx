import { ReportTable } from "@/components/report-table";
import { listReports } from "@/lib/reports";

export default function Home() {
  const reports = listReports();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Research reports</h1>
        {reports.length > 0 && (
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            {reports.length} {reports.length === 1 ? "report" : "reports"} · latest {reports[0].date}
          </p>
        )}
      </div>
      {reports.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
          No reports published yet.
        </p>
      ) : (
        <ReportTable reports={reports} />
      )}
    </div>
  );
}
