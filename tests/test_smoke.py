import pytest

from stock_researcher.cli import main


def test_version(capsys):
    assert main(["--version"]) == 0
    assert "0.1.0" in capsys.readouterr().out


def test_stub_not_implemented(capsys):
    assert main(["verify-citations", "AAPL"]) == 2  # still a stub (S5)
    assert "not implemented" in capsys.readouterr().err


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "stock_researcher" in capsys.readouterr().out
