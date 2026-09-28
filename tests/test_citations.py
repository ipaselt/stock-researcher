import json
import os
import shutil
from pathlib import Path

import pytest

from stock_researcher import citations, cli
from stock_researcher.citations import check_json_block, check_prose, verify

from .conftest import FakeProvider
from .test_report import aapl, age, do_assemble, run_dir, write_agents, write_verdict  # noqa: F401 (fixtures)

AGENT_OUTPUTS = Path(__file__).parent / "fixtures" / "agent_outputs"
REAL = ["technicals", "valuation"]


@pytest.fixture
def aapl_data(tmp_cwd, monkeypatch, capsys):
    """data/AAPL.json + AAPL.score.json from the AAPL fixture, and the two real agent outputs in data/AAPL/."""
    monkeypatch.setattr(cli, "get_provider", lambda: FakeProvider())
    assert cli.main(["run", "AAPL"]) == 0
    for agent in REAL:
        shutil.copy(AGENT_OUTPUTS / f"{agent}.md", tmp_cwd / "data" / "AAPL" / f"{agent}.md")
    capsys.readouterr()
    return tmp_cwd / "data"


@pytest.fixture
def sources(aapl_data):
    return {"snapshot": json.loads((aapl_data / "AAPL.json").read_text(encoding="utf-8")),
            "score": json.loads((aapl_data / "AAPL.score.json").read_text(encoding="utf-8"))}


def edit(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def block(numbers, **extra):
    fields = {"dimension": "x", "grade": "B", "confidence": "low", "numbers_cited": numbers, **extra}
    return f"## X\n### Findings\n- text\n```json\n{json.dumps(fields)}\n```\n"


# --- the real agent outputs ---------------------------------------------------------------------------------

def test_real_fixtures_pass(aapl_data, capsys):
    assert cli.main(["verify-citations", "AAPL"]) == 0
    assert capsys.readouterr().out.splitlines() == ["PASS technicals", "PASS valuation",
                                                    "wrote data/AAPL/citations.json"]
    written = json.loads((aapl_data / "AAPL" / "citations.json").read_text(encoding="utf-8"))
    assert written == {a: {"status": "PASS", "failures": []} for a in REAL}


def test_fabricated_json_number_fails(aapl_data, sources, capsys):
    edit(aapl_data / "AAPL" / "valuation.md", '"valuation.forward_pe", "value": 35.486446}',
         '"valuation.forward_pe", "value": 28.1}')
    assert cli.main(["verify-citations", "AAPL"]) == 1
    ref = sources["snapshot"]["valuation"]["forward_pe"]
    line = f"valuation: valuation.forward_pe cited 28.1 vs {ref:.4g} in snapshot"
    assert capsys.readouterr().out.splitlines() == ["PASS technicals", "FAIL valuation", f"  {line}",
                                                    "wrote data/AAPL/citations.json"]
    written = json.loads((aapl_data / "AAPL" / "citations.json").read_text(encoding="utf-8"))
    assert written["valuation"] == {"status": "FAIL", "failures": [line]}


def test_fabricated_prose_number_fails(aapl_data, sources):
    path = aapl_data / "AAPL" / "valuation.md"
    edit(path, "forward P/E of 35.5x (valuation.forward_pe) and a trailing",
         "forward P/E 99.0x (valuation.forward_pe) and a trailing")
    ref = sources["snapshot"]["valuation"]["forward_pe"]
    assert verify("AAPL", aapl_data)["valuation"]["failures"] == [
        f"valuation: valuation.forward_pe cited 99.0x vs {ref:.4g}x in snapshot"]


def test_json_key_from_score_file_resolves(sources):
    assert check_json_block("a", block([{"key": "categories.momentum.score", "value": 100.0},
                                        {"key": "fair_value.n_years", "value": 4}]), sources) == []


# --- prose rules (small synthetic sources) ------------------------------------------------------------------

SRC = {"snapshot": {"profitability": {"fcf_margin": 0.2308}, "health": {"free_cashflow": 107721875456.0,
                                                                         "interest_coverage": None},
                    "valuation": {"fcf_yield": 0.0217, "earnings_yield": 0.0249, "fiscal_year_pe": [34.0, 22.2]},
                    "technical": {"golden_cross": True}, "events": {"next_earnings_date": "2026-10-29"},
                    "analyst": {"upside": -0.136}},
       "score": {"fair_value": {"n_years": 4}}}


@pytest.mark.parametrize("prose", [
    "FCF margin 23.1% (profitability.fcf_margin)",       # percent -> fraction
    "free cash flow $107.7B (health.free_cashflow)",     # B -> 1e9, $ as-is
    "FCF yield 2.2% (valuation.fcf_yield)",              # honest one-decimal rounding of 2.17%
    "from 22.2x to 34.0x (valuation.fiscal_year_pe)",    # a list reference: any element
    "upside -13.6% (analyst.upside)",
    "due 2026-10-29 (events.next_earnings_date)",        # a date is not a number claim
    "the golden cross (technical.golden_cross = true)",
    "margin (profitability.fcf_margin 23.1%)",           # the value written inside the parentheses
    "over 4 years (fair_value.n_years), 107.7B (health.free_cashflow, fair_value.n_years)",
    "no coverage figure (health.interest_coverage)",     # a null field cited without a number
])
def test_prose_passes(prose):
    assert check_prose("a", prose, SRC) == []


@pytest.mark.parametrize("prose, failure", [
    ("unknown (valuation.bogus)", "a: prose cites unknown key (valuation.bogus)"),
    ("coverage 12.0x (health.interest_coverage)",
     "a: health.interest_coverage cited 12.0x for a null field (cited a value for a null field)"),
    ("earnings yield 2% (valuation.earnings_yield)", "a: valuation.earnings_yield cited 2% vs 2.49% in snapshot"),
    ("upside 13.6% (analyst.upside)", "a: analyst.upside cited 13.6% vs -13.6% in snapshot"),
    ("margin (profitability.fcf_margin 33.1%)", "a: profitability.fcf_margin cited 33.1% vs 23.08% in snapshot"),
    ("cross (technical.golden_cross = false)", "a: technical.golden_cross cited false vs true in snapshot"),
    ("pe 50.0x (valuation.fiscal_year_pe)", "a: valuation.fiscal_year_pe cited 50.0x vs 34x, 22.2x in snapshot"),
])
def test_prose_fails(prose, failure):
    assert check_prose("a", prose, SRC) == [failure]


def test_json_block_rules():
    ok = [{"key": "health.interest_coverage", "value": None}, {"key": "technical.golden_cross", "value": True},
          {"key": "valuation.fiscal_year_pe", "value": [34.1, 22.2]},
          {"key": "events.next_earnings_date", "value": "2026-10-29"}]
    assert check_json_block("a", block(ok), SRC) == []
    bad = [{"key": "health.interest_coverage", "value": 3.0}, {"key": "technical.golden_cross", "value": 1},
           {"key": "valuation.fiscal_year_pe", "value": [34.0]}, {"key": "nope.key", "value": 1}]
    assert check_json_block("a", block(bad), SRC) == [
        "a: health.interest_coverage cited 3 vs null in snapshot",
        "a: technical.golden_cross cited 1 vs true in snapshot",
        "a: valuation.fiscal_year_pe cited [34] vs [34, 22.2] in snapshot",
        "a: nope.key not found in snapshot or score",
    ]


def test_zero_reference_uses_absolute_tolerance():
    assert citations.values_match(0.0, 0) and not citations.values_match(0.001, 0.0)


@pytest.mark.parametrize("text, failure", [
    ("## X\nno block here (health.free_cashflow)\n", "a: no ```json block found"),
    ("## X\n```json\n{not json}\n```\n", "a: json block does not parse"),
    (block([]).replace('"grade": "B", ', ""), "a: json block missing grade"),
])
def test_bad_json_block(text, failure):
    assert check_json_block("a", text, SRC)[0].startswith(failure)


def test_missing_json_block_fails_the_agent(aapl_data, capsys):
    (aapl_data / "AAPL" / "growth-quality.md").write_text("## Growth\n- revenue grew\n", encoding="utf-8")
    assert cli.main(["verify-citations", "AAPL"]) == 1
    out = capsys.readouterr().out
    assert "FAIL growth-quality\n  growth-quality: no ```json block found" in out


# --- files and exit codes ----------------------------------------------------------------------------------

def test_empty_file_skipped_and_skeleton_verdict_ignored(aapl_data, capsys):
    (aapl_data / "AAPL" / "news-catalysts.md").write_text("  \n", encoding="utf-8")
    (aapl_data / "AAPL" / "verdict.md").write_text("no json here (bogus.key)", encoding="utf-8")
    assert set(verify("AAPL", aapl_data)) == set(REAL)


@pytest.mark.parametrize("missing", ["AAPL.json", "AAPL.score.json"])
def test_missing_snapshot_or_score_exits_2(aapl_data, missing, capsys):
    (aapl_data / missing).unlink()
    assert cli.main(["verify-citations", "AAPL"]) == 2
    assert "missing" in capsys.readouterr().err
    assert not (aapl_data / "AAPL" / "citations.json").exists()


def test_no_agent_files_exits_2(aapl_data, capsys):
    for agent in REAL:
        (aapl_data / "AAPL" / f"{agent}.md").unlink()
    assert cli.main(["verify-citations", "AAPL"]) == 2
    assert "no agent reports" in capsys.readouterr().err
    assert not (aapl_data / "AAPL" / "citations.json").exists()


def test_bad_ticker_exits_2(tmp_cwd, capsys):
    assert cli.main(["verify-citations", "1ABC"]) == 2
    assert "invalid ticker" in capsys.readouterr().err


# --- assemble reads citations.json -------------------------------------------------------------------------

def write_citations(run_dir, results):
    (run_dir / "citations.json").write_text(json.dumps(results), encoding="utf-8")


def appendix(tmp_cwd):
    return do_assemble(tmp_cwd).read_text(encoding="utf-8").split("## Appendix")[1]


FIVE = ["valuation", "growth-quality", "balance-sheet-risk", "technicals", "news-catalysts"]


def test_assemble_without_citations_json(tmp_cwd, run_dir):
    write_agents(run_dir, FIVE)
    write_verdict(run_dir)
    assert "citation check: not run" in appendix(tmp_cwd)


def test_assemble_renders_pass(tmp_cwd, run_dir):
    write_agents(run_dir, FIVE)
    write_verdict(run_dir)
    write_citations(run_dir, {a: {"status": "PASS", "failures": []} for a in FIVE})
    text = appendix(tmp_cwd)
    assert "citation check: PASS (5/5 agents)" in text and "not run" not in text


def test_assemble_renders_fail_and_skips_dropped_agents(tmp_cwd, run_dir):
    write_agents(run_dir, ["valuation", "growth-quality", "balance-sheet-risk", "technicals"])
    (run_dir / "news-catalysts.md").write_text("", encoding="utf-8")  # dropped after failing twice
    write_verdict(run_dir)
    results = {a: {"status": "PASS", "failures": []} for a in FIVE}
    results["valuation"] = {"status": "FAIL", "failures": ["v: a", "v: b"]}
    results["technicals"] = {"status": "FAIL", "failures": ["t: a"]}
    results["news-catalysts"] = {"status": "FAIL", "failures": ["n: a"]}
    write_citations(run_dir, results)
    assert "citation check: FAIL — valuation: 2 mismatches; technicals: 1 mismatch\n" in appendix(tmp_cwd)


def test_assemble_ignores_stale_citations_json(tmp_cwd, run_dir):
    write_agents(run_dir, FIVE)
    write_verdict(run_dir)
    write_citations(run_dir, {a: {"status": "PASS", "failures": []} for a in FIVE})
    age(run_dir / "citations.json", seconds=1)  # an agent file changed after verify-citations
    text = appendix(tmp_cwd)
    assert "citation check: not run" in text
    assert "- stale citations.json ignored" in text


def test_verify_then_assemble_end_to_end(aapl_data, capsys):
    run = aapl_data / "AAPL"
    for agent in ["growth-quality", "balance-sheet-risk", "news-catalysts"]:
        shutil.copy(run / "technicals.md", run / f"{agent}.md")  # stand-ins that cite real keys
    write_verdict(run)
    assert cli.main(["verify-citations", "AAPL"]) == 0
    capsys.readouterr()
    assert cli.main(["assemble", "AAPL", "--date", "2026-09-28"]) == 0
    text = (aapl_data.parent / "reports" / "AAPL-2026-09-28.md").read_text(encoding="utf-8")
    assert "citation check: PASS (5/5 agents)" in text


def test_unreadable_score_exits_2(aapl_data, capsys):
    (aapl_data / "AAPL.score.json").write_text("{not json", encoding="utf-8")
    assert cli.main(["verify-citations", "AAPL"]) == 2
    assert "verify-citations AAPL:" in capsys.readouterr().err
