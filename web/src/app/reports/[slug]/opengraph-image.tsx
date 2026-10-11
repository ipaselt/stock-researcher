import { ImageResponse } from "next/og";
import { getReport, listReports } from "@/lib/reports";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const dynamicParams = false;

export function generateStaticParams() {
  return listReports().map((r) => ({ slug: r.slug }));
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const meta = getReport((await params).slug)?.meta;
  return new ImageResponse(
    (
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: "100%", height: "100%", padding: 72, background: "#0a0a0a", color: "#ededed" }}>
        <div style={{ fontSize: 40, color: "#a1a1aa" }}>Stock Researcher</div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 160, fontWeight: 700 }}>{meta?.ticker ?? "?"}</div>
          <div style={{ fontSize: 48 }}>{meta ? `${meta.labelFinal} · ${meta.score ?? "—"} / 100 · ${meta.date}` : ""}</div>
        </div>
        <div style={{ fontSize: 24, color: "#71717a" }}>Generated research for the owner&apos;s own process. Not investment advice.</div>
      </div>
    ),
    size,
  );
}
