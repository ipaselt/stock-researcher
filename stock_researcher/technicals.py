"""Technical indicators and return math over a daily close series. Pure pandas — no yfinance.

Standard textbook formulations (pattern copied from portfolio-lab): simple moving averages,
Wilder-smoothed RSI, relative strength as a ratio of cumulative returns, plus period returns,
max drawdown and CAGR. All returns are fractions (0.12 = 12%).
"""
import pandas as pd

# A period return needs history reaching back to (about) its start date; allow for weekends/holidays.
_START_SLACK = pd.Timedelta(days=7)


def sma(close, window):
    """Simple moving average of a close series."""
    return close.rolling(window).mean()


def rsi(close, window=14):
    """Relative Strength Index, Wilder smoothing (the standard 14-period formulation)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    # avg_loss of 0 (all gains) makes RS inf → RSI resolves to exactly 100; the first
    # `window` rows stay NaN (warm-up).
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def relative_strength(close, bench_close):
    """Cumulative-return ratio vs. a benchmark, rebased to 1.0 at the first shared date.

    > 1 means the ticker has outperformed the benchmark since the window start.
    """
    joined = pd.concat({"t": close, "b": bench_close}, axis=1).dropna()
    t_rebased = joined["t"] / joined["t"].iloc[0]
    b_rebased = joined["b"] / joined["b"].iloc[0]
    return t_rebased / b_rebased


def _return_since(close, start):
    """Total return from the last close on/before `start` to the latest close; None if history is too short."""
    close = close.dropna()
    if close.empty or close.index[0] > start + _START_SLACK:
        return None
    base = close[close.index <= start]
    base_price = base.iloc[-1] if not base.empty else close.iloc[0]
    if base_price <= 0:
        return None
    return float(close.iloc[-1] / base_price - 1)


def trailing_return(close, years):
    """Total return over the trailing `years` calendar years ending at the last close."""
    if close.dropna().empty:
        return None
    return _return_since(close, close.dropna().index[-1] - pd.DateOffset(years=years))


def ytd_return(close):
    """Total return from the prior year's last close to the latest close."""
    close = close.dropna()
    if close.empty:
        return None
    end = close.index[-1]
    prior_year_end = pd.Timestamp(year=end.year - 1, month=12, day=31, tz=end.tz)
    # YTD needs the prior year's close itself, so no start slack here.
    if close.index[0] > prior_year_end:
        return None
    return _return_since(close, prior_year_end)


def period_returns(close):
    """YTD / 1y / 3y / 5y total returns as fractions (None where history is too short)."""
    return {
        "ytd": ytd_return(close),
        "1y": trailing_return(close, 1),
        "3y": trailing_return(close, 3),
        "5y": trailing_return(close, 5),
    }


def max_drawdown(close, window_days=252):
    """Worst peak-to-trough decline over the last `window_days` closes, as a fraction ≤ 0 (None if empty)."""
    recent = close.dropna().iloc[-window_days:]
    if recent.empty:
        return None
    return float((recent / recent.cummax() - 1).min())


def cagr(first, last, years):
    """Compound annual growth rate; None if either value is missing/≤ 0 or years ≤ 0."""
    if first is None or last is None or years is None or first <= 0 or last <= 0 or years <= 0:
        return None
    return (last / first) ** (1 / years) - 1
