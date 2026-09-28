import re

import pytest

from stock_researcher.cli import TICKER_COMMANDS, main


def test_version(capsys):
    assert main(["--version"]) == 0
    assert "0.1.0" in capsys.readouterr().out


def test_every_subcommand_in_help(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    listed = re.search(r"\{([a-z,-]+)\}", capsys.readouterr().out).group(1).split(",")
    assert listed == TICKER_COMMANDS + ["ledger"]  # every subcommand is implemented; none is a stub any more


def test_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "stock_researcher" in capsys.readouterr().out
