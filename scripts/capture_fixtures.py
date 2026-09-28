"""Capture offline test fixtures for one ticker (real network calls; run by hand, never from tests).

Usage: python scripts/capture_fixtures.py AAPL
Writes tests/fixtures/<T>_{info.json,income_stmt.json,history.csv,news.json,targets.json,earnings_dates.json}.
A symbol Yahoo doesn't know gets only <T>_info.json (whatever near-empty dict Yahoo returns).
"""
import json
import sys
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stock_researcher.providers.yfinance_provider import YFinanceProvider  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def capture(ticker: str) -> None:
    info = yf.Ticker(ticker).info or {}
    write_json(FIXTURES / f"{ticker}_info.json", info)
    if info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
        print(f"{ticker}: no price in info — wrote info only")
        return
    provider = YFinanceProvider()
    history = provider.fetch_history(ticker, period="5y")
    history = history[["Open", "High", "Low", "Close", "Volume"]]
    history.index = history.index.tz_localize(None).date
    history.index.name = "Date"
    history.to_csv(FIXTURES / f"{ticker}_history.csv", float_format="%.8g", encoding="utf-8")  # 8 sig. digits keeps sub-penny prices
    income = provider.fetch_income_stmt(ticker)
    (FIXTURES / f"{ticker}_income_stmt.json").write_text(
        income.to_json(orient="split", date_format="iso"), encoding="utf-8"
    )
    write_json(FIXTURES / f"{ticker}_news.json", provider.fetch_news(ticker, limit=10))
    write_json(FIXTURES / f"{ticker}_targets.json", provider.fetch_analyst_targets(ticker))
    write_json(FIXTURES / f"{ticker}_earnings_dates.json", provider.fetch_earnings_dates(ticker))
    print(f"{ticker}: {len(history)} history rows, income_stmt {income.shape}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        capture(arg.upper())
