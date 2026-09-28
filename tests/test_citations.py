import json
import re
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
       "score": {"fair_value": {"n_years": 4}, "total": 60.1, "coverage_pct": 0.94}}


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
    text = do_assemble(tmp_cwd).read_text(encoding="utf-8")
    assert "citation check: FAIL — valuation: 2 mismatches; technicals: 1 mismatch\n" in text
    for agent in ("valuation", "technicals"):  # withheld from the report
        assert f"{agent} says hello." not in text
        assert f"- {agent} failed the citation check; its section is withheld" in text
    assert text.count("_(agent failed citation check)_") == 2
    assert "growth-quality says hello." in text


def test_assemble_ignores_stale_citations_json(tmp_cwd, run_dir):
    write_agents(run_dir, FIVE)
    write_verdict(run_dir)
    write_citations(run_dir, {a: {"status": "PASS", "failures": []} for a in FIVE})
    age(run_dir / "skeleton.md", seconds=120)  # citations.json stays newer than the skeleton ...
    age(run_dir / "citations.json", seconds=1)  # ... but older than the agent files: one changed after the check
    assert (run_dir / "skeleton.md").stat().st_mtime < (run_dir / "citations.json").stat().st_mtime
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


# --- mutation: every decimal the real fixtures print is guarded --------------------------------------------

MUTATION_EXCEPTIONS: dict[str, str] = {}  # "file: number" -> why a x1.5 change of it cannot be caught


@pytest.mark.parametrize("name", sorted(p.name for p in AGENT_OUTPUTS.glob("*.md")))
def test_inflating_any_printed_decimal_fails(name, sources):
    """Each decimal in the prose, reason and flags, inflated x1.5 one at a time, must produce a failure.
    Decimals inside numbers_cited are the JSON-block check's job and are covered by its own tests."""
    text = (AGENT_OUTPUTS / name).read_text(encoding="utf-8")
    start = text.index('"numbers_cited"')
    end = text.index("\n ],", start)
    missed, count = [], 0
    for m in re.finditer(r"\d+\.\d+", text):
        if start <= m.start() < end or f"{name}: {m.group(0)}" in MUTATION_EXCEPTIONS:
            continue
        decimals = len(m.group(0).split(".")[1])
        mutated = text[:m.start()] + f"{float(m.group(0)) * 1.5:.{decimals}f}" + text[m.end():]
        count += 1
        if not check_json_block("x", mutated, sources) + check_prose("x", mutated, sources):
            missed.append(text[max(0, m.start() - 40):m.end() + 20])
    assert count > 20 and missed == []


# --- v1.1 rules: windows, uncited numbers, units, syntax -------------------------------------------------

@pytest.mark.parametrize("prose", [
    "free cash flow of 107.7 billion (health.free_cashflow)",
    "free cash flow of $107.7bn (health.free_cashflow)",
    "free cash flow of 107,721.9 million (health.free_cashflow)",
    "a 22.2 times multiple (valuation.fiscal_year_pe)",
    "a 22.2X multiple (valuation.fiscal_year_pe)",
    "margin of **23.1%** (profitability.fcf_margin)",           # emphasis stripped
    "margin of _23.1%_ (`profitability.fcf_margin`)",           # backticks inside the parentheses
    "margin (profitability.fcf_margin: 23.1%)",                  # ':' as the inline separator
    "a score of 60.1 (total) at 94.0% coverage (coverage_pct)",  # single-segment score keys
    "from 22.2x to 34.0x (valuation.fiscal_year_pe)",            # every number in the window
    "FCF 23.1% and yield 2.2% (profitability.fcf_margin, valuation.fcf_yield)",
    "the 3-year and 1-5 year view of the S&P 500 in 2025, RSI(14) and 1 year: 23.1% (profitability.fcf_margin)",
    "a margin of 23.1% (profitability.fcf_margin), well above the 10 peers",  # trailing plain integer ignored
    "Revenue grew in 12 of the last 20 quarters.",               # plain integers in an uncited sentence
    "sales of the iPhone 18 (profitability.fcf_margin)",         # a model number, not a claim
])
def test_prose_passes_v11(prose):
    assert check_prose("a", prose, SRC) == []


@pytest.mark.parametrize("prose, failure", [
    ("from 99.0x to 34.0x (valuation.fiscal_year_pe)",
     "a: valuation.fiscal_year_pe cited 99.0x vs 34x, 22.2x in snapshot"),        # not only the last number
    ("FCF 23.1% and yield 9.9% (profitability.fcf_margin, valuation.fcf_yield)",
     "a: 9.9% matches none of profitability.fcf_margin (23.08%); valuation.fcf_yield (2.17%)"),
    ("RSI of 66.2 is not overbought.", 'a: uncited number 66.2 in: "RSI of 66.2 is not overbought."'),
    ("margin 23.1% (profitability.fcf_margin), up 4.0% on the year",
     'a: uncited number 4.0% in: "margin 23.1% (profitability.fcf_margin), up 4.0% on the year"'),
    ("cash of $5 is small.", 'a: uncited number $5 in: "cash of $5 is small."'),
    ("yield up 25 bps (valuation.fcf_yield)", "a: unsupported unit in 25bps (restate as % or x)"),
    ("margin up 2 pp (profitability.fcf_margin)", "a: unsupported unit in 2pp (restate as % or x)"),
    ("a score of 70.0 (total)", "a: total cited 70.0 vs 60.1 in score"),
    ("margin **33.1%** (profitability.fcf_margin)", "a: profitability.fcf_margin cited 33.1% vs 23.08% in snapshot"),
    ("mean 2.2 (events.next_earnings_date)", 'a: events.next_earnings_date cited 2.2 vs "2026-10-29" in snapshot'),
])
def test_prose_fails_v11(prose, failure):
    assert check_prose("a", prose, SRC) == [failure]


def test_plain_parenthesised_words_are_not_citations():
    assert check_prose("a", "Apple (the company) and margins (strong).", SRC) == []


def test_reason_and_flags_are_checked():
    text = block([], reason="FCF margin 33.1% (profitability.fcf_margin).", flags=["extended: 18.2% above"])
    assert check_json_block("a", text, SRC) == [
        "a: profitability.fcf_margin cited 33.1% vs 23.08% in snapshot",
        'a: uncited number 18.2% in: "extended: 18.2% above"',
    ]
    assert check_json_block("a", block([], reason="FCF margin 23.1% (profitability.fcf_margin).",
                                       flags=["method_fit:ok"]), SRC) == []


def test_more_than_one_json_block_fails():
    assert check_json_block("a", block([]) + block([]), SRC) == ["a: 2 ```json blocks found; exactly one allowed"]


def test_scalar_cited_for_a_list_reference():
    assert check_json_block("a", block([{"key": "valuation.fiscal_year_pe", "value": 22.2}]), SRC) == []
    assert check_json_block("a", block([{"key": "valuation.fiscal_year_pe", "value": 50.0}]), SRC) == [
        "a: valuation.fiscal_year_pe cited 50 vs [34, 22.2] in snapshot"]


@pytest.mark.parametrize("content", ["[1, 2]", "{not json", '{"valuation": {"status": "PASS"}}'])
def test_assemble_tolerates_wrong_shape_citations_json(tmp_cwd, run_dir, content):
    write_agents(run_dir, FIVE)
    write_verdict(run_dir)
    (run_dir / "citations.json").write_text(content, encoding="utf-8")
    text = appendix(tmp_cwd)
    assert "citation check: not run" in text and "- unreadable citations.json ignored" in text
