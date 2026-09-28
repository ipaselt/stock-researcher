"""Network canaries against real Yahoo data. Excluded by default; run with `pytest -m live`."""
import pytest

from stock_researcher.providers import TickerNotFound, get_provider
from stock_researcher.scorecard import score_snapshot
from stock_researcher.snapshot import build_snapshot

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def no_network():
    """Overrides conftest's autouse guard of the same name: these tests are the only ones allowed on the network."""


def test_aapl_live():
    snapshot = build_snapshot(get_provider(), "AAPL")
    assert snapshot.meta.price
    assert score_snapshot(snapshot).coverage_pct >= 0.8
    assert snapshot.meta.warnings == []


def test_nvda_split_consistency():
    """Closes are split-adjusted; a fiscal year whose Diluted EPS is not restated for NVDA's 2024 10:1 split
    shows up as a ~10x jump in year-end P/E between adjacent years."""
    pes = build_snapshot(get_provider(), "NVDA").valuation.fiscal_year_pe
    print(f"NVDA fiscal_year_pe (most recent first): {pes}")
    assert pes
    assert all(5 <= pe <= 200 for pe in pes)
    assert all(max(a, b) / min(a, b) <= 4 for a, b in zip(pes, pes[1:]))


def test_unknown_ticker_live():
    with pytest.raises(TickerNotFound):
        build_snapshot(get_provider(), "ZZZZZZ")
