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
    assert capsys.readouterr().out.strip() == "wrote data/AAPL.json (0 fields missing, 0 warnings)"


@pytest.mark.parametrize("bad", ["1ABC", "TOOLONGX", "A B", "$AAPL", ""])
def test_snapshot_rejects_bad_ticker(tmp_cwd, fake_cli_provider, bad, capsys):
    assert cli.main(["snapshot", bad]) == 2
    assert "invalid ticker" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


def test_snapshot_unknown_ticker(tmp_cwd, fake_cli_provider, capsys):
    assert cli.main(["snapshot", "ZZZZZZ"]) == 2
    assert "not found" in capsys.readouterr().err
    assert not (tmp_cwd / "data").exists()


def test_snapshot_dotted_ticker_passes_validation(tmp_cwd, fake_cli_provider, capsys):
    # BRK.B is a valid symbol shape; with no fixture the fake provider reports it unknown.
    assert cli.main(["snapshot", "brk.b"]) == 2
    assert "not found" in capsys.readouterr().err
