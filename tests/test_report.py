import dataclasses
import os
import json

import pytest

from stock_researcher import report
from stock_researcher.fair_value import compute_fair_value
from stock_researcher.labels import suggest_label
from stock_researcher.report import AGENTS, FRONT_MATTER_KEYS, OPTIONAL_AGENTS, assemble, render_skeleton
from stock_researcher.scorecard import METRICS, score_snapshot
from stock_researcher.snapshot import build_snapshot

from .conftest import FakeProvider

HEADINGS = ["Header", "Verdict", "Scorecard", "Fair value and entry price", "Valuation", "Growth and quality",
            "Balance sheet and risk", "Technicals and timing", "News and catalysts", "Bear case", "Synthesis",
            "Appendix"]
VERDICT = """---
label_final: {label}
entry_target: 250.80
override_reason: {reason}
---
### Thesis
Great business, full price.

### Key risks
- China demand

### What changes my mind
A price under the entry.

### Triggers
- Next earnings
"""


def scored(ticker):
    snapshot = build_snapshot(FakeProvider(), ticker, as_of="2026-09-28")
    score = score_snapshot(snapshot)
    fv = compute_fair_value(snapshot, score.total)
    return snapshot, score, fv, suggest_label(score, fv, snapshot)


@pytest.fixture(scope="module")
def aapl():
    return scored("AAPL")


@pytest.fixture
def skeleton(aapl):
    return render_skeleton(*aapl)


def headings(text):
    return [line[3:] for line in text.splitlines() if line.startswith("## ")]


def test_skeleton_headings_in_order(skeleton):
    assert headings(skeleton) == HEADINGS


def test_skeleton_one_scorecard_row_per_metric(skeleton):
    section = skeleton.split("## Scorecard")[1].split("\n\n| Category | Weight")[0]
    rows = [line for line in section.splitlines() if line.startswith("| ") and "`" in line]
    assert len(rows) == len(METRICS)
    for row, metric in zip(rows, METRICS):
        assert row.startswith(f"| {metric.category} | `{metric.field.split('.')[1]}` |")
    assert "| health | `interest_coverage` | — | — | — | 6 | no reported interest expense |" in rows


def test_skeleton_markers_present(skeleton):
    for agent in AGENTS + OPTIONAL_AGENTS:
        assert f"\n<!-- AGENT: {agent} -->\n" in skeleton
    for marker in (report.VERDICT_MARKER, report.SYNTHESIS_MARKER, report.ASSEMBLY_MARKER):
        assert f"\n{marker}\n" in skeleton


def test_skeleton_content(skeleton):
    assert "| Suggested label | HAS RUN (L7) |" in skeleton
    assert "| Score | 60.1/100 (good) |" in skeleton
    assert "= **$295.06**" in skeleton and "= **$250.80**" in skeleton
    assert "median year-end P/E of the last 4 fiscal years" in skeleton
    assert report.STATED_LIMITS in skeleton and report.STATED_LIMITS.startswith("- Banks")
    assert "- health.interest_coverage" in skeleton
    assert "citation check: not run" in skeleton
    for doc in ("docs/scorecard.md", "docs/fair-value.md", "docs/labels.md"):
        assert doc in skeleton
    assert skeleton.rstrip().endswith(report.DISCLAIMER)


def test_skeleton_without_fair_value():
    text = render_skeleton(*scored("RIVN"))
    assert headings(text) == HEADINGS
    assert "No fair value: forward EPS -1.74 <= 0." in text
    assert "| Entry target | — |" in text


@pytest.mark.parametrize("field, value, expected", [
    ("profitability.gross_margin", 0.4868, "48.7%"),
    ("growth.earnings_growth_yoy", -0.1, "-10.0%"),
    ("valuation.forward_pe", 35.62, "35.6x"),
    ("health.debt_to_equity", 0.784, "0.8x"),
    ("valuation.peg", None, "—"),
])
def test_fmt_value(field, value, expected):
    assert report.fmt_value(field, value) == expected


def test_multiples_are_scorecard_fields():
    assert report.MULTIPLES <= {m.field for m in METRICS}


def test_front_matter_round_trip():
    values = {"a": "1", "b": "none", "c": "x: y"}
    assert report.parse_front_matter(report.front_matter(values) + "body\n") == (values, "body")
    assert report.parse_front_matter("no fence\n") is None
    assert report.parse_front_matter("---\na: 1\n") is None  # unclosed
    assert report.parse_front_matter("---\nnot a pair\n---\n") is None


def test_front_matter_quotes_yaml_unsafe_values():
    text = report.front_matter({"override_reason": "none", "a": "x: y", "b": "#tag", "c": 'say "hi"', "d": "plain"})
    assert text.splitlines()[1:-1] == ['override_reason: "none"', 'a: "x: y"', 'b: "#tag"', 'c: "say \\"hi\\""',
                                       "d: plain"]
    fields, _ = report.parse_front_matter(text)
    assert fields == {"override_reason": "none", "a": "x: y", "b": "#tag", "c": 'say "hi"', "d": "plain"}


def test_parse_front_matter_single_quotes_and_blank_lines():
    fields, body = report.parse_front_matter("---\na: 'quoted'\n\nb: 2\n---\nbody")
    assert fields == {"a": "quoted", "b": "2"} and body == "body"


def test_fmt_money_sub_dollar():
    assert report.fmt_money(0.0001) == "$0.0001"
    assert report.fmt_money(0.5) == "$0.5000"
    assert report.fmt_money(1234.5) == "$1,234.50"


def test_skeleton_sub_penny_price():
    text = render_skeleton(*scored("HCMC"))
    assert "| Price | $0.0001 |" in text and "$0.00 " not in text


# --- assemble ---------------------------------------------------------------------------------------------

@pytest.fixture
def run_dir(tmp_cwd, aapl):
    snapshot, score, fv, label = aapl
    data = tmp_cwd / "data"
    (data / "AAPL").mkdir(parents=True)
    (data / "AAPL" / "skeleton.md").write_text(render_skeleton(*aapl), encoding="utf-8")
    result = {"price": snapshot.meta.price, "total": score.total, "coverage_pct": score.coverage_pct,
              "fair_value": dataclasses.asdict(fv), "label_suggestion": dataclasses.asdict(label)}
    (data / "AAPL.score.json").write_text(json.dumps(result), encoding="utf-8")
    return data / "AAPL"


def write_agents(run_dir, agents):
    for agent in agents:
        (run_dir / f"{agent}.md").write_text(f"### Findings\n{agent} says hello.\n", encoding="utf-8")


def write_verdict(run_dir, label="HAS RUN", reason="none"):
    (run_dir / "verdict.md").write_text(VERDICT.format(label=label, reason=reason), encoding="utf-8")


def do_assemble(tmp_cwd, today="2026-09-28"):
    return assemble("AAPL", tmp_cwd / "data", tmp_cwd / "reports", today)


def test_assemble_fills_every_slot(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS + OPTIONAL_AGENTS)
    write_verdict(run_dir)
    out = do_assemble(tmp_cwd)
    assert out == tmp_cwd / "reports" / "AAPL-2026-09-28.md"
    text = out.read_text(encoding="utf-8")
    assert "<!--" not in text
    for agent in AGENTS + OPTIONAL_AGENTS:
        assert f"{agent} says hello." in text
    fields, body = report.parse_front_matter(text)
    assert tuple(fields) == FRONT_MATTER_KEYS
    assert fields == {
        "date": "2026-09-28", "ticker": "AAPL", "price": "341.655", "score": "60.1", "coverage": "0.94",
        "fair_value": "295.06", "entry": "250.8", "label_suggested": "HAS RUN", "rule_id": "L7",
        "label_final": "HAS RUN", "override_reason": "none", "report": "reports/AAPL-2026-09-28.md",
    }
    assert headings(body) == HEADINGS
    verdict = body.split("## Verdict")[1].split("## Scorecard")[0]
    assert "**Final label: HAS RUN** (entry target $250.80); confirms the suggested HAS RUN (L7)." in verdict
    assert "Great business, full price." in verdict and "### Key risks" not in verdict
    synthesis = body.split("## Synthesis")[1].split("## Appendix")[0]
    assert "Rule fired: **L7**" in synthesis
    for part in ("### Key risks", "### What changes my mind", "### Triggers"):
        assert part in synthesis
    assert "### Thesis" not in synthesis
    assert "Assembly warnings:\n\n- none" in body


def test_assemble_drops_bear_case_and_marks_missing_agent(tmp_cwd, run_dir):
    write_agents(run_dir, [a for a in AGENTS if a != "technicals"])
    write_verdict(run_dir)
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert headings(text) == [h for h in HEADINGS if h != "Bear case"]
    technicals = text.split("## Technicals and timing")[1].split("\n## ")[0]
    assert "_(agent did not report)_" in technicals
    assert "- technicals agent did not report" in text
    assert "<!--" not in text


def test_assemble_override(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    write_verdict(run_dir, label="WAIT", reason="L7 -> WAIT: 1y relative return (performance.rel_1y) is modest")
    fields, body = report.parse_front_matter(do_assemble(tmp_cwd).read_text(encoding="utf-8"))
    assert (fields["label_suggested"], fields["label_final"]) == ("HAS RUN", "WAIT")
    assert fields["override_reason"] == "L7 -> WAIT: 1y relative return (performance.rel_1y) is modest"
    assert "overrides the suggested HAS RUN (L7): L7 -> WAIT" in body


def test_assemble_errors_without_verdict(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    with pytest.raises(FileNotFoundError, match="verdict"):
        do_assemble(tmp_cwd)
    assert not (tmp_cwd / "reports").exists()


def test_assemble_errors_without_skeleton(tmp_cwd, run_dir):
    (run_dir / "skeleton.md").unlink()
    write_verdict(run_dir)
    with pytest.raises(FileNotFoundError, match="skeleton"):
        do_assemble(tmp_cwd)


@pytest.mark.parametrize("verdict, match", [
    ("### Thesis\nno front-matter\n", "no front-matter"),
    ("---\nlabel_final: WAIT\n---\nbody\n", "missing entry_target, override_reason"),
    ("---\nlabel_final: MAYBE\nentry_target: none\noverride_reason: x\n---\nbody\n", "not one of"),
    ("---\nlabel_final: WAIT\nentry_target: none\noverride_reason: none\n---\nbody\n", "without an override_reason"),
    ("---\nlabel_final: HAS RUN\nentry_target: cheap\noverride_reason: none\n---\nbody\n", "not a number"),
    ("---\nlabel_final: HAS RUN\nentry_target: nan\noverride_reason: none\n---\nbody\n", "not a number"),
    ("---\nlabel_final: HAS RUN\nentry_target: none\noverride_reason: none\n---\n\n", "body is empty"),
], ids=["no-front-matter", "missing-keys", "bad-label", "silent-override", "bad-entry", "nan-entry", "empty-body"])
def test_assemble_rejects_bad_verdict(tmp_cwd, run_dir, verdict, match):
    (run_dir / "verdict.md").write_text(verdict, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        do_assemble(tmp_cwd)


def test_assemble_entry_none(tmp_cwd, run_dir):
    (run_dir / "verdict.md").write_text(
        "---\nlabel_final: HAS RUN\nentry_target: none\noverride_reason: none\n---\n### Thesis\nx\n",
        encoding="utf-8")
    fields, _ = report.parse_front_matter(do_assemble(tmp_cwd).read_text(encoding="utf-8"))
    assert fields["entry"] == "none"


def test_same_day_rerun_overwrites(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    write_verdict(run_dir)
    first = do_assemble(tmp_cwd)
    (run_dir / "valuation.md").write_text("second pass\n", encoding="utf-8")
    second = do_assemble(tmp_cwd)
    assert first == second
    assert list((tmp_cwd / "reports").iterdir()) == [second]
    text = second.read_text(encoding="utf-8")
    assert "second pass" in text and "valuation says hello." not in text


def age(path, seconds=60):
    """Make `path` older than it is (older than skeleton.md written just before it)."""
    st = path.stat()
    os.utime(path, (st.st_atime - seconds, st.st_mtime - seconds))


def test_stale_agent_files_count_as_missing(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS + OPTIONAL_AGENTS)
    write_verdict(run_dir)
    age(run_dir / "technicals.md")
    age(run_dir / "bear-case.md")
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert "technicals says hello." not in text and "bear-case says hello." not in text
    assert headings(text) == [h for h in HEADINGS if h != "Bear case"]
    assert "- stale technicals.md ignored (older than skeleton.md)" in text
    assert "- stale bear-case.md ignored (older than skeleton.md)" in text
    assert "- technicals agent did not report" in text


def test_stale_verdict_is_an_error(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    write_verdict(run_dir)
    age(run_dir / "verdict.md")
    with pytest.raises(ValueError, match="stale verdict"):
        do_assemble(tmp_cwd)
    assert not (tmp_cwd / "reports").exists()


def test_bear_case_heading_inside_agent_text_survives(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    news = "### Findings\n\n## Bear case\n\nThe news agent quotes a heading.\n"
    (run_dir / "news-catalysts.md").write_text(news, encoding="utf-8")
    write_verdict(run_dir)
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert news.strip() in text
    assert "<!--" not in text
    assert text.count("## Bear case") == 1  # the one inside the news section
    assert "## Synthesis" in text


def test_marker_text_inside_agent_file_is_not_expanded(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    (run_dir / "valuation.md").write_text("see <!-- AGENT: growth-quality --> and\n<!-- AGENT: growth-quality -->\n",
                                          encoding="utf-8")
    write_verdict(run_dir)
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert text.count("growth-quality says hello.") == 1
    assert text.count("<!-- AGENT: growth-quality -->") == 2  # only the valuation agent's literal text


def test_confirm_with_note_says_confirms(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    write_verdict(run_dir, reason="checked (valuation.forward_pe)")
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert "confirms the suggested HAS RUN (L7): checked (valuation.forward_pe)." in text
    assert "overrides" not in text


def test_verdict_bom_blank_lines_and_no_thesis(tmp_cwd, run_dir):
    write_agents(run_dir, AGENTS)
    (run_dir / "verdict.md").write_text(
        "\ufeff---\nlabel_final: HAS RUN\n\nentry_target: 250.80\noverride_reason: none\n---\n### Key risks\n- x\n",
        encoding="utf-8")
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert "**Final label: HAS RUN**" in text
    assert "- verdict.md has no '### Thesis' heading" in text
    assert "### Key risks" in text.split("## Synthesis")[1]
