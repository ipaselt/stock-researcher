import json
from pathlib import Path

import pandas as pd
import pytest
import yfinance

from stock_researcher.providers import TickerNotFound, get_provider
from stock_researcher.providers.yfinance_provider import YFinanceProvider

FIXTURES = Path(__file__).parent / "fixtures"


class _StubTicker:
    def __init__(self, info):
        self.info = info


def test_near_empty_info_raises_ticker_not_found(monkeypatch):
    unknown = json.loads((FIXTURES / "ZZZZZZ_info.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _StubTicker(unknown))
    with pytest.raises(TickerNotFound):
        YFinanceProvider().fetch_info("ZZZZZZ")


def test_info_with_only_regular_market_price_is_found(monkeypatch):
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _StubTicker({"regularMarketPrice": 10.0}))
    assert YFinanceProvider().fetch_info("SPY") == {"regularMarketPrice": 10.0}


def test_get_provider():
    assert isinstance(get_provider(), YFinanceProvider)
    with pytest.raises(ValueError):
        get_provider("nope")


def test_network_guard_blocks_yfinance():
    with pytest.raises(RuntimeError, match="network call in test"):
        yfinance.Ticker("AAPL")
    with pytest.raises(RuntimeError, match="network call in test"):
        get_provider().fetch_info("AAPL")


def test_fake_provider_round_trips_fixtures(fake_provider):
    info = fake_provider.fetch_info("AAPL")
    assert info == json.loads((FIXTURES / "AAPL_info.json").read_text(encoding="utf-8"))

    history = fake_provider.fetch_history("AAPL")
    assert isinstance(history.index, pd.DatetimeIndex)
    assert {"Open", "High", "Low", "Close", "Volume"} <= set(history.columns)
    assert len(history) > 1000 and history.index.is_monotonic_increasing

    income = fake_provider.fetch_income_stmt("AAPL")
    assert isinstance(income.columns[0], pd.Timestamp)
    assert list(income.columns) == sorted(income.columns, reverse=True)
    assert "Total Revenue" in income.index

    assert 0 < len(fake_provider.fetch_news("AAPL", limit=3)) <= 3
    assert set(fake_provider.fetch_analyst_targets("AAPL")) >= {"mean", "median", "high", "low"}
    assert all(len(d) == 10 for d in fake_provider.fetch_earnings_dates("AAPL"))


def test_fake_provider_unknown_ticker(fake_provider):
    with pytest.raises(TickerNotFound):
        fake_provider.fetch_info("ZZZZZZ")
    with pytest.raises(TickerNotFound):
        fake_provider.fetch_info("NOFIXTURE")
