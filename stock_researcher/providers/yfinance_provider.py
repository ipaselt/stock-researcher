"""yfinance-backed DataProvider. Raw values out — no unit logic here."""
import datetime as dt

import pandas as pd
import yfinance as yf

from .base import TickerNotFound


class YFinanceProvider:
    name = f"yfinance {yf.__version__}"

    def fetch_info(self, ticker: str) -> dict:
        info = yf.Ticker(ticker).info or {}
        # Yahoo answers an unknown symbol with a near-empty dict rather than an error.
        if info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
            raise TickerNotFound(ticker)
        return info

    def fetch_history(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        return yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)

    def fetch_income_stmt(self, ticker: str) -> pd.DataFrame:
        return yf.Ticker(ticker).income_stmt

    def fetch_news(self, ticker: str, limit: int = 10) -> list[dict]:
        return list(yf.Ticker(ticker).news or [])[:limit]

    def fetch_analyst_targets(self, ticker: str) -> dict:
        return dict(yf.Ticker(ticker).analyst_price_targets or {})

    def fetch_earnings_dates(self, ticker: str) -> list[str]:
        calendar = yf.Ticker(ticker).calendar or {}
        dates = calendar.get("Earnings Date") or []
        return [d.isoformat()[:10] for d in dates if isinstance(d, dt.date)]
