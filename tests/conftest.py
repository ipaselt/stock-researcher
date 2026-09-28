import io
import json
from pathlib import Path

import pandas as pd
import pytest
import yfinance

from stock_researcher.providers import TickerNotFound

FIXTURES = Path(__file__).parent / "fixtures"


class FakeProvider:
    """DataProvider backed by the committed fixtures in tests/fixtures/ (captured by scripts/capture_fixtures.py)."""

    name = "fake"

    def _path(self, ticker, suffix):
        return FIXTURES / f"{ticker}_{suffix}"

    def _json(self, ticker, suffix, default):
        path = self._path(ticker, suffix)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    def fetch_info(self, ticker):
        info = self._json(ticker, "info.json", {})
        if info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
            raise TickerNotFound(ticker)
        return info

    def fetch_history(self, ticker, period="5y"):
        path = self._path(ticker, "history.csv")
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, index_col="Date", parse_dates=True, encoding="utf-8")

    def fetch_income_stmt(self, ticker):
        path = self._path(ticker, "income_stmt.json")
        if not path.exists():
            return pd.DataFrame()
        df = pd.read_json(io.StringIO(path.read_text(encoding="utf-8")), orient="split")
        df.columns = pd.to_datetime(df.columns)
        return df

    def fetch_news(self, ticker, limit=10):
        return self._json(ticker, "news.json", [])[:limit]

    def fetch_analyst_targets(self, ticker):
        return self._json(ticker, "targets.json", {})

    def fetch_earnings_dates(self, ticker):
        return self._json(ticker, "earnings_dates.json", [])


def _no_network(*args, **kwargs):
    raise RuntimeError("network call in test")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(yfinance, "Ticker", _no_network)
    monkeypatch.setattr(yfinance, "download", _no_network)


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path
