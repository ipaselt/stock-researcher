import { describe, expect, it } from "vitest";
import { parseFrontMatter } from "./frontmatter";

const REASON =
  "L6 suggested BUY; overriding to WAIT because the entry price 687.47 (fair_value.entry_price) sits above the target: 515.0 (analyst.target_high).";

const NVDA = [
  "---",
  "date: 2026-09-28",
  "ticker: NVDA",
  "price: 229.6099",
  "label_suggested: BUY",
  "rule_id: L6",
  "label_final: WAIT",
  `override_reason: ${JSON.stringify(REASON)}`,
  "report: reports/NVDA-2026-09-28.md",
  "---",
  "",
  "# NVDA — NVIDIA Corporation",
].join("\n");

describe("parseFrontMatter", () => {
  it("round-trips a JSON-quoted override with a colon and a semicolon; keeps values as strings", () => {
    const parsed = parseFrontMatter(NVDA);
    expect(parsed).not.toBeNull();
    expect(parsed!.fields.override_reason).toBe(REASON);
    expect(parsed!.fields.date).toBe("2026-09-28");
    expect(parsed!.fields.price).toBe("229.6099");
    expect(parsed!.fields.label_final).toBe("WAIT");
    expect(parsed!.body).toBe("\n# NVDA — NVIDIA Corporation");
  });

  it('maps override_reason: "none" to null', () => {
    const parsed = parseFrontMatter('---\nticker: AAA\noverride_reason: "none"\nentry: none\n---\nbody');
    expect(parsed!.fields.override_reason).toBeNull();
    expect(parsed!.fields.entry).toBeNull();
  });

  it("returns null on a malformed line", () => {
    expect(parseFrontMatter("---\nticker: AAA\nno colon here\n---\n")).toBeNull();
    expect(parseFrontMatter("---\n: empty key\n---\n")).toBeNull();
  });

  it("returns null without an opening or closing fence", () => {
    expect(parseFrontMatter("ticker: AAA\n---\n")).toBeNull();
    expect(parseFrontMatter("---\nticker: AAA\n")).toBeNull();
  });

  it("parses CRLF input", () => {
    const parsed = parseFrontMatter(NVDA.replace(/\n/g, "\r\n"));
    expect(parsed!.fields.override_reason).toBe(REASON);
    expect(parsed!.fields.report).toBe("reports/NVDA-2026-09-28.md");
    expect(parsed!.body).toBe("\n# NVDA — NVIDIA Corporation");
  });
});
