import csv

from stock_researcher import ledger
from stock_researcher.report import front_matter

HEADER = "date,ticker,price,score,coverage,fair_value,entry,label_suggested,rule_id,label_final,report"


def write_report(reports, date, ticker, **overrides):
    values = {"date": date, "ticker": ticker, "price": "100.5", "score": "61.2", "coverage": "0.94",
              "fair_value": "120.0", "entry": "102.0", "label_suggested": "WAIT", "rule_id": "L8",
              "label_final": "WAIT", "override_reason": "none", "report": f"reports/{ticker}-{date}.md"}
    values.update(overrides)
    (reports / f"{ticker}-{date}.md").write_text(front_matter(values) + "\n# body\n", encoding="utf-8")


def read_rows(reports):
    with (reports / "ratings.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_header_exact_and_columns():
    assert ",".join(ledger.COLUMNS) == HEADER


def test_rebuild_empty(tmp_path):
    assert ledger.rebuild(tmp_path) == 0
    assert (tmp_path / "ratings.csv").read_text(encoding="utf-8").splitlines() == [HEADER]


def test_rebuild_one(tmp_path):
    write_report(tmp_path, "2026-09-28", "AAPL")
    assert ledger.rebuild(tmp_path) == 1
    (row,) = read_rows(tmp_path)
    assert row == {"date": "2026-09-28", "ticker": "AAPL", "price": "100.5", "score": "61.2", "coverage": "0.94",
                   "fair_value": "120.0", "entry": "102.0", "label_suggested": "WAIT", "rule_id": "L8",
                   "label_final": "WAIT", "report": "reports/AAPL-2026-09-28.md"}


def test_rebuild_three_sorted_none_empty_stray_skipped(tmp_path):
    write_report(tmp_path, "2026-09-29", "MSFT")
    write_report(tmp_path, "2026-09-28", "RIVN", fair_value="none", entry="none", label_suggested="NOT LOOKING",
                 rule_id="L4", label_final="NOT LOOKING")
    write_report(tmp_path, "2026-09-28", "AAPL", score="None")
    (tmp_path / "notes.md").write_text("# no front-matter here\n", encoding="utf-8")
    (tmp_path / "broken.md").write_text("---\nticker: X\n", encoding="utf-8")  # unclosed fence
    assert ledger.rebuild(tmp_path) == 3
    rows = read_rows(tmp_path)
    assert [(r["date"], r["ticker"]) for r in rows] == [
        ("2026-09-28", "AAPL"), ("2026-09-28", "RIVN"), ("2026-09-29", "MSFT")]
    assert rows[0]["score"] == ""
    assert (rows[1]["fair_value"], rows[1]["entry"]) == ("", "")
    lines = (tmp_path / "ratings.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER and len(lines) == 4
    assert "override_reason" not in lines[0]


def test_rebuild_overwrites_previous_csv(tmp_path):
    write_report(tmp_path, "2026-09-28", "AAPL")
    ledger.rebuild(tmp_path)
    (tmp_path / "AAPL-2026-09-28.md").unlink()
    assert ledger.rebuild(tmp_path) == 0
    assert read_rows(tmp_path) == []
