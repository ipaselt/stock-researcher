// Mirror of stock_researcher/report.py `parse_front_matter` + `_unquote` (+ `is_none` → null).
// Values stay strings: no Date or number coercion.

export type FrontMatter = { fields: Record<string, string | null>; body: string };

function unquote(value: string): string {
  if (value.length >= 2 && value[0] === '"' && value[value.length - 1] === '"') {
    try {
      return String(JSON.parse(value));
    } catch {
      return value;
    }
  }
  if (value.length >= 2 && value[0] === "'" && value[value.length - 1] === "'") {
    return value.slice(1, -1);
  }
  return value;
}

export function parseFrontMatter(text: string): FrontMatter | null {
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== "---") return null;
  const fields: Record<string, string | null> = {};
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === "---") return { fields, body: lines.slice(i + 1).join("\n") };
    if (!line.trim()) continue;
    const at = line.indexOf(":");
    if (at < 0) return null;
    const key = line.slice(0, at).trim();
    if (!key) return null;
    const value = unquote(line.slice(at + 1).trim());
    fields[key] = value.trim().toLowerCase() === "none" || value.trim() === "" ? null : value;
  }
  return null; // no closing fence
}
