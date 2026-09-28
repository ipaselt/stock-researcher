import json

import pytest

from stock_researcher import cli


@pytest.fixture
def fake_cli_provider(monkeypatch, fake_provider):
    monkeypatch.setattr(cli, "get_provider", lambda: fake_provider)


def test_snapshot_writes_json(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "aapl"]) == 0
    data = json.loads((tmp_cwd / "data" / "AAPL.json").read_text(encoding="utf-8"))
    assert data["meta"]["ticker"] == "AAPL"
    n_missing, n_warnings = len(data["meta"]["fields_missing"]), len(data["meta"]["warnings"])
    assert n_missing == 1  # health.interest_coverage
    assert capsys.readouterr().out.strip() == f"wrote data/AAPL.json ({n_missing} fields missing, {n_warnings} warnings)"


@pytest.mark.parametrize("bad", ["1ABC", "TOOLONGX", "A B", "$AAPL", "", "AAPL\n", "COM1", "LPT9"])
def test_snapshot_rejects_bad_ticker(tmp_cwd, fake_cli_provider, bad, capsys):
    assert cli.main(["snapshot", bad]) == 2
    assert "invalid ticker" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


@pytest.mark.parametrize("reserved", ["con", "PRN", "AUX", "NUL", "CON.A"])  # COM1-9/LPT1-9 already fail the regex
def test_snapshot_rejects_windows_device_names(tmp_cwd, fake_cli_provider, reserved, capsys):
    assert cli.main(["snapshot", reserved]) == 2
    assert "reserved" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


def test_snapshot_unknown_ticker(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "ZZZZZZ"]) == 2
    assert "not found" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


def test_snapshot_dotted_ticker_passes_validation(tmp_cwd, fake_cli_provider, capsys):
    # BRK.B is a valid symbol shape; with no fixture the fake provider reports it unknown.
    assert cli.main(["snapshot", "brk.b"]) == 2
    assert "not found" in capsys.readouterr().err


SCORE_KEYS = ["ticker", "as_of", "price", "total", "band_word", "coverage_pct", "categories", "metrics",
              "fair_value", "label_suggestion"]


def _strict_json(text):
    def reject(constant):
        raise ValueError(f"non-finite constant {constant}")
    return json.loads(text, parse_constant=reject)


def test_score_end_to_end(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "AAPL"]) == 0
    capsys.readouterr()
    assert cli.main(["score", "aapl"]) == 0
    data = _strict_json((tmp_cwd / "data" / "AAPL.score.json").read_text(encoding="utf-8"))
    assert list(data) == SCORE_KEYS
    assert data["ticker"] == "AAPL" and data["as_of"] and data["price"] == 341.655
    assert set(data["categories"]) == {"valuation", "growth", "profitability", "health", "momentum"}
    assert len(data["metrics"]) == 18
    coverage = next(m for m in data["metrics"] if m["field"] == "health.interest_coverage")
    assert not coverage["covered"] and coverage["note"] == "no reported interest expense"
    assert data["coverage_pct"] == 0.94
    fv, label = data["fair_value"], data["label_suggestion"]
    assert fv["fair_pe_source"] == "historical_median" and fv["n_years"] == 4
    # Pinned AAPL fixture outputs (hand-reproduced in the independent review).
    assert data["total"] == 60.1 and data["band_word"] == "good"
    assert fv["fair_pe"] == pytest.approx(30.782, abs=1e-3)
    assert fv["fair_value"] == pytest.approx(295.057, abs=1e-3)
    assert fv["entry_price"] == pytest.approx(250.799, abs=1e-3)
    assert (label["label"], label["rule_id"]) == ("HAS RUN", "L7")
    assert label["entry_target"] == pytest.approx(250.799, abs=1e-3)
    entry = "n/a" if label["entry_target"] is None else f"{label['entry_target']:.2f}"
    assert capsys.readouterr().out.strip() == (
        f"AAPL: score {data['total']:.1f} ({data['band_word']}), coverage 94%, "
        f"label {label['label']} ({label['rule_id']}), entry {entry}"
    )


def test_score_sparse_ticker_is_not_looking(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "HCMC"]) == 0
    assert cli.main(["score", "HCMC"]) == 0
    data = _strict_json((tmp_cwd / "data" / "HCMC.score.json").read_text(encoding="utf-8"))
    assert data["label_suggestion"]["rule_id"] == "L1"
    assert data["fair_value"]["fair_value"] is None


def test_score_missing_snapshot(tmp_cwd, capsys):
    assert cli.main(["score", "AAPL"]) == 2
    assert "no snapshot" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


@pytest.mark.parametrize("bad", ["1ABC", "CON"])
def test_score_rejects_bad_ticker(tmp_cwd, bad, capsys):
    assert cli.main(["score", bad]) == 2
    assert capsys.readouterr().err


def test_score_rivn_l5_cites_eps(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "RIVN"]) == 0
    assert cli.main(["score", "RIVN"]) == 0
    data = _strict_json((tmp_cwd / "data" / "RIVN.score.json").read_text(encoding="utf-8"))
    assert data["fair_value"]["reason"] == "forward EPS -1.74 <= 0"


@pytest.mark.parametrize("content", ['{"meta": {"ticker": "AAPL"', '{"meta": {"ticker": "AAPL", "bogus_key": 1}}'],
                         ids=["truncated", "unknown-key"])
def test_score_unreadable_snapshot(tmp_cwd, content, capsys):
    (tmp_cwd / "data").mkdir()
    (tmp_cwd / "data" / "AAPL.json").write_text(content, encoding="utf-8")
    assert cli.main(["score", "AAPL"]) == 2
    assert capsys.readouterr().err.startswith("unreadable snapshot data/AAPL.json: ")
    assert not (tmp_cwd / "data" / "AAPL.score.json").exists()


# --- run / assemble / ledger (S3) -------------------------------------------------------------------------

def test_run_end_to_end(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["run", "aapl"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[0].startswith("wrote data/AAPL.json")
    assert out[1] == "AAPL: score 60.1 (good), coverage 94%, label HAS RUN (L7), entry 250.80"
    assert out[2] == "wrote data/AAPL/skeleton.md"
    data = _strict_json((tmp_cwd / "data" / "AAPL.score.json").read_text(encoding="utf-8"))
    assert data["total"] == 60.1
    assert data["fair_value"]["entry_price"] == pytest.approx(250.799, abs=1e-3)
    skeleton = (tmp_cwd / "data" / "AAPL" / "skeleton.md").read_text(encoding="utf-8")
    assert "| Suggested label | HAS RUN (L7) |" in skeleton and "= **$250.80**" in skeleton


def test_run_regenerates(tmp_cwd, fake_cli_provider, capsys):
    (tmp_cwd / "data" / "AAPL").mkdir(parents=True)
    for name in ("skeleton.md", "bear-case.md", "verdict.md", "valuation.md"):
        (tmp_cwd / "data" / "AAPL" / name).write_text("stale", encoding="utf-8")
    assert cli.main(["run", "AAPL"]) == 0
    assert (tmp_cwd / "data" / "AAPL" / "skeleton.md").read_text(encoding="utf-8").startswith("# AAPL")
    assert sorted(p.name for p in (tmp_cwd / "data" / "AAPL").iterdir()) == ["skeleton.md"]


def test_assemble_rejects_quoted_none_override(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["run", "AAPL"]) == 0
    _write_run_inputs(tmp_cwd)
    (tmp_cwd / "data" / "AAPL" / "verdict.md").write_text(
        '---\nlabel_final: WAIT\nentry_target: 250.80\noverride_reason: "none"\n---\n### Thesis\nx\n',
        encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["assemble", "AAPL", "--date", "2026-09-28"]) == 2
    assert "without an override_reason" in capsys.readouterr().err
    assert not (tmp_cwd / "reports").exists()


@pytest.mark.parametrize("ticker, err", [("ZZZZZZ", "not found"), ("1ABC", "invalid ticker")])
def test_run_ticker_errors(tmp_cwd, fake_cli_provider, ticker, err, capsys):
    assert cli.main(["run", ticker]) == 2
    assert err in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


def _write_run_inputs(tmp_cwd):
    run_dir = tmp_cwd / "data" / "AAPL"
    for agent in ["valuation", "growth-quality", "balance-sheet-risk", "technicals", "news-catalysts"]:
        (run_dir / f"{agent}.md").write_text(f"{agent} finding.\n", encoding="utf-8")
    (run_dir / "verdict.md").write_text(
        "---\nlabel_final: HAS RUN\nentry_target: 250.80\noverride_reason: none\n---\n"
        "### Thesis\nQuality at a full price.\n\n### Key risks\n- valuation\n", encoding="utf-8")


def test_assemble_and_ledger_end_to_end(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["run", "AAPL"]) == 0
    _write_run_inputs(tmp_cwd)
    capsys.readouterr()
    assert cli.main(["assemble", "aapl", "--date", "2026-09-28"]) == 0
    assert capsys.readouterr().out.splitlines() == ["wrote reports/AAPL-2026-09-28.md", "ledger: 1 rows"]
    report = (tmp_cwd / "reports" / "AAPL-2026-09-28.md").read_text(encoding="utf-8")
    assert report.startswith("---\ndate: 2026-09-28\nticker: AAPL\n")
    assert "Quality at a full price." in report and "## Bear case" not in report
    csv_lines = (tmp_cwd / "reports" / "ratings.csv").read_text(encoding="utf-8").splitlines()
    assert csv_lines[1] == "2026-09-28,AAPL,341.655,60.1,0.94,295.06,250.8,HAS RUN,L7,HAS RUN,reports/AAPL-2026-09-28.md"
    assert cli.main(["ledger"]) == 0
    assert capsys.readouterr().out.strip() == "ledger: 1 rows"


def test_assemble_missing_verdict(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["run", "AAPL"]) == 0
    capsys.readouterr()
    assert cli.main(["assemble", "AAPL"]) == 2
    assert "missing verdict" in capsys.readouterr().err
    assert not (tmp_cwd / "reports").exists()


def test_assemble_missing_skeleton(tmp_cwd, capsys):
    assert cli.main(["assemble", "AAPL"]) == 2
    assert "missing skeleton" in capsys.readouterr().err


def test_assemble_bad_date(tmp_cwd, capsys):
    assert cli.main(["assemble", "AAPL", "--date", "28/09/2026"]) == 2
    assert "invalid --date" in capsys.readouterr().err


def test_ledger_empty(tmp_cwd, capsys):
    assert cli.main(["ledger"]) == 0
    assert capsys.readouterr().out.strip() == "ledger: 0 rows"


# --- run --offline (S5) -------------------------------------------------------------------------------------

def test_run_offline_reuses_todays_snapshot(tmp_cwd, fake_cli_provider, monkeypatch, capsys):
    assert cli.main(["run", "AAPL"]) == 0
    snap = tmp_cwd / "data" / "AAPL.json"
    before = (snap.read_bytes(), snap.stat().st_mtime_ns)
    (tmp_cwd / "data" / "AAPL" / "valuation.md").write_text("old run", encoding="utf-8")
    (tmp_cwd / "data" / "AAPL.score.json").unlink()
    monkeypatch.setattr(cli, "get_provider", lambda: pytest.fail("--offline must not fetch"))
    capsys.readouterr()
    assert cli.main(["run", "AAPL", "--offline"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "AAPL: score 60.1 (good), coverage 94%, label HAS RUN (L7), entry 250.80", "wrote data/AAPL/skeleton.md"]
    assert (snap.read_bytes(), snap.stat().st_mtime_ns) == before
    assert (tmp_cwd / "data" / "AAPL.score.json").exists()
    assert sorted(p.name for p in (tmp_cwd / "data" / "AAPL").iterdir()) == ["skeleton.md"]


@pytest.mark.parametrize("as_of", ["2020-01-02", None])  # None: no snapshot file at all
def test_run_offline_without_fresh_snapshot(tmp_cwd, fake_cli_provider, as_of, capsys):
    if as_of:
        assert cli.main(["snapshot", "AAPL"]) == 0
        snap = tmp_cwd / "data" / "AAPL.json"
        data = json.loads(snap.read_text(encoding="utf-8"))
        data["meta"]["as_of"] = as_of
        snap.write_text(json.dumps(data), encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["run", "AAPL", "--offline"]) == 2
    assert capsys.readouterr().err.strip() == "no fresh snapshot for AAPL; run without --offline"
    assert not (tmp_cwd / "data" / "AAPL.score.json").exists()
    assert not (tmp_cwd / "data" / "AAPL" / "skeleton.md").exists()
