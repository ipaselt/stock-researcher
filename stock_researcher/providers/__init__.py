from .base import DataProvider, TickerNotFound


def get_provider(name: str = "yfinance") -> DataProvider:
    if name == "yfinance":
        from .yfinance_provider import YFinanceProvider

        return YFinanceProvider()
    raise ValueError(f"unknown provider {name!r}")


__all__ = ["DataProvider", "TickerNotFound", "get_provider"]
