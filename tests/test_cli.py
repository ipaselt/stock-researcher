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
