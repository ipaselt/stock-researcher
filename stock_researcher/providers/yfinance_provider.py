"""yfinance-backed DataProvider. Raw values out — no unit logic here."""
import datetime as dt
import time

import pandas as pd
import yfinance as yf

from .base import TickerNotFound

RETRY_DELAYS = (1, 2)  # seconds slept before the 2nd and 3rd attempt
_sleep = time.sleep  # module-level so tests can monkeypatch it


def _retry(fetch, retry_empty: bool = False):
    """fetch() with up to 3 attempts; TickerNotFound is an answer, not a transient failure, so it is not retried.

    retry_empty: an empty result also counts as a failure (yfinance's history() swallows errors and returns an
    empty frame); after the last attempt the empty result is returned as-is.
    """
    for delay in RETRY_DELAYS:
        try:
            result = fetch()
            if not (retry_empty and result.empty):
                return result
        except TickerNotFound:
            raise
        except Exception:
            pass
        _sleep(delay)
    return fetch()  # the last attempt: its error (or empty result) propagates


class YFinanceProvider:
    name = f"yfinance {yf.__version__}"

    def fetch_info(self, ticker: str) -> dict:
        def fetch():
            info = yf.Ticker(ticker).info or {}
            # Yahoo answers an unknown symbol with a near-empty dict rather than an error.
            if info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
                raise TickerNotFound(ticker)
            return info
        return _retry(fetch)

    def fetch_history(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        return _retry(lambda: yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True),
                      retry_empty=True)

    def fetch_income_stmt(self, ticker: str) -> pd.DataFrame:
        return _retry(lambda: yf.Ticker(ticker).income_stmt)

    def fetch_news(self, ticker: str, limit: int = 10) -> list[dict]:
        return _retry(lambda: list(yf.Ticker(ticker).news or [])[:limit])

    def fetch_analyst_targets(self, ticker: str) -> dict:
        return _retry(lambda: dict(yf.Ticker(ticker).analyst_price_targets or {}))

    def fetch_earnings_dates(self, ticker: str) -> list[str]:
        def fetch():
            calendar = yf.Ticker(ticker).calendar or {}
            dates = calendar.get("Earnings Date") or []
            return [d.isoformat()[:10] for d in dates if isinstance(d, dt.date)]
        return _retry(fetch)
