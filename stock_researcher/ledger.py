"""The ratings ledger: reports/ratings.csv, derived from every report's front-matter (never edited by hand)."""
import csv
from pathlib import Path

from .report import parse_front_matter

COLUMNS = ["date", "ticker", "price", "score", "coverage", "fair_value", "entry", "label_suggested", "rule_id",
           "label_final", "report"]


def _cell(value: str | None) -> str:
    return "" if value is None or value.lower() == "none" else value


def rebuild(reports_dir) -> int:
    """Rewrite reports_dir/ratings.csv from the front-matter of every reports_dir/*.md; return the row count.

    Files without a front-matter carrying `date` and `ticker` are skipped.
    """
    reports_dir = Path(reports_dir)
    rows = []
    for path in sorted(reports_dir.glob("*.md")):
        parsed = parse_front_matter(path.read_text(encoding="utf-8"))
        if parsed is None or not parsed[0].get("date") or not parsed[0].get("ticker"):
            continue
        rows.append({c: _cell(parsed[0].get(c)) for c in COLUMNS})
    rows.sort(key=lambda r: (r["date"], r["ticker"]))
    reports_dir.mkdir(parents=True, exist_ok=True)
    with (reports_dir / "ratings.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
