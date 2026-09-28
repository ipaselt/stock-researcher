import json
from pathlib import Path

import pandas as pd
import pytest
import yfinance

from stock_researcher.providers import TickerNotFound, get_provider
from stock_researcher.providers import yfinance_provider
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


class _FlakyTicker:
    """Stands in for yfinance.Ticker: `failures` constructions raise, then it returns `info`."""

    def __init__(self, failures, error=ConnectionError("rate limited")):
        self.calls, self.failures, self.error = 0, failures, error

    def __call__(self, symbol):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return _StubTicker({"currentPrice": 1.0})


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(yfinance_provider, "_sleep", calls.append)
    return calls


def test_retry_succeeds_on_third_attempt(monkeypatch, sleeps):
    flaky = _FlakyTicker(failures=2)
    monkeypatch.setattr(yfinance, "Ticker", flaky)
    assert YFinanceProvider().fetch_info("AAPL") == {"currentPrice": 1.0}
    assert flaky.calls == 3 and sleeps == [1, 2]


def test_ticker_not_found_is_not_retried(monkeypatch, sleeps):
    calls = []
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: calls.append(symbol) or _StubTicker({}))
    with pytest.raises(TickerNotFound):
        YFinanceProvider().fetch_info("ZZZZZZ")
    assert calls == ["ZZZZZZ"] and sleeps == []


def test_three_failures_reraise_last_error(monkeypatch, sleeps):
    flaky = _FlakyTicker(failures=3, error=ConnectionError("still down"))
    monkeypatch.setattr(yfinance, "Ticker", flaky)
    with pytest.raises(ConnectionError, match="still down"):
        YFinanceProvider().fetch_history("AAPL")
    assert flaky.calls == 3 and sleeps == [1, 2]


class _HistoryTicker:
    def __init__(self, frame):
        self.frame = frame

    def history(self, **kwargs):
        return self.frame


def test_empty_history_is_retried_then_returned(monkeypatch, sleeps):
    frames = [pd.DataFrame(), pd.DataFrame({"Close": [1.0]})]
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _HistoryTicker(frames.pop(0)))
    assert list(YFinanceProvider().fetch_history("AAPL")["Close"]) == [1.0]
    assert sleeps == [1]
    calls = []
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: calls.append(symbol) or _HistoryTicker(pd.DataFrame()))
    assert YFinanceProvider().fetch_history("AAPL").empty  # still empty after 3 attempts: returned, not raised
    assert len(calls) == 3 and sleeps == [1, 1, 2]
