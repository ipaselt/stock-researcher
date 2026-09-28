"""The DataProvider Protocol — the only abstraction in the project.

A provider returns raw data exactly as the source gives it; unit handling lives in normalize.py.
"""
from typing import Protocol

import pandas as pd


class TickerNotFound(Exception):
    """The provider has no data for this symbol."""


class DataProvider(Protocol):
    name: str

    def fetch_info(self, ticker: str) -> dict:
        """Raw quote/fundamentals dict. Raises TickerNotFound for unknown symbols."""
        ...

    def fetch_history(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        """Daily auto-adjusted OHLCV with a DatetimeIndex."""
        ...

    def fetch_income_stmt(self, ticker: str) -> pd.DataFrame:
        """Annual income statement: columns = fiscal year-end Timestamps (most recent first), rows = line items."""
        ...

    def fetch_news(self, ticker: str, limit: int = 10) -> list[dict]:
        """Raw news items (yfinance shape: data nested under 'content')."""
        ...

    def fetch_analyst_targets(self, ticker: str) -> dict:
        """current/high/low/mean/median price targets, or {}."""
        ...

    def fetch_earnings_dates(self, ticker: str) -> list[str]:
        """Upcoming/recent earnings dates as ISO strings, possibly empty."""
        ...
