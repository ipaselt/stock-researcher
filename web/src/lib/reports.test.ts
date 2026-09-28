import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SLUG_RE, cleanBody, firstSentence, listReports, parseReport, slug } from "./reports";

const DIR = path.join(__dirname, "..", "..", "test", "fixtures", "reports");
const read = (stem: string) => fs.readFileSync(path.join(DIR, `${stem}.md`), "utf-8");

describe("listReports", () => {
  const reports = listReports(DIR);

  it("sorts date desc then ticker asc", () => {
    expect(reports.map((r) => r.slug)).toEqual(["BBB-2026-02-01", "AAA-2026-01-01"]);
  });

  it('maps override "none" to null and keeps a quoted override with a colon', () => {
    const [bbb, aaa] = reports;
    expect(aaa.overrideReason).toBeNull();
    expect(bbb.overrideReason).toContain("(valuation.ev_ebitda)");
    expect(bbb.overrideReason).toContain("ratio: 3.1x");
  });

  it("reads meta: name, numbers, labels, thesis", () => {
    const [bbb, aaa] = reports;
    expect(bbb.name).toBe("Beta Test Inc.");
    expect(bbb.price).toBe(42);
    expect(bbb.entry).toBe(38);
    expect(aaa.entry).toBeNull();
    expect(bbb.labelSuggested).toBe("BUY");
    expect(bbb.ruleId).toBe("L6");
    expect(bbb.labelFinal).toBe("WAIT");
    expect(bbb.thesis).toBe("Beta is a strong business at a full price. Wait for 38.");
  });
});

describe("parseReport", () => {
  it("drops the H1 and the nested agent H2, keeps the section H2", () => {
    const report = parseReport("BBB-2026-02-01", read("BBB-2026-02-01"))!;
    expect(report.body).not.toContain("# BBB — Beta Test Inc.");
    expect(report.body).not.toContain("## Valuation — BBB");
    expect(report.body).toContain("## Valuation\n");
    expect(report.sections.map((s) => s.id)).toEqual(["verdict", "valuation", "synthesis"]);
  });

  it("rejects a bad slug", () => {
    expect(parseReport("../etc", read("AAA-2026-01-01"))).toBeNull();
  });
});

describe("helpers", () => {
  it("SLUG_RE guards traversal", () => {
    expect(SLUG_RE.test("BRK.B-2026-01-01")).toBe(true);
    expect(SLUG_RE.test("../AAA-2026-01-01")).toBe(false);
  });

  it("cleanBody escapes the ticker", () => {
    expect(cleanBody("## Valuation — BRKXB\n## Valuation — BRK.B", "BRK.B")).toBe("## Valuation — BRKXB");
  });

  it("slug and firstSentence", () => {
    expect(slug("News & Catalysts — NVDA")).toBe("news-catalysts-nvda");
    expect(firstSentence("One two. Three.")).toBe("One two.");
    expect(firstSentence("x".repeat(300)).length).toBeLessThanOrEqual(160);
  });
});
