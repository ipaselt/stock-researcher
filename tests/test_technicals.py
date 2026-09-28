import math

import pandas as pd
import pytest

from stock_researcher import technicals


def _series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_sma():
    out = technicals.sma(_series([1, 2, 3, 4, 5]), 2)
    assert math.isnan(out.iloc[0])
    assert out.iloc[1:].tolist() == [1.5, 2.5, 3.5, 4.5]


def test_rsi_extremes_and_bounds():
    assert technicals.rsi(_series(range(1, 40))).iloc[-1] == pytest.approx(100.0)
    assert technicals.rsi(_series(range(40, 1, -1))).iloc[-1] == pytest.approx(0.0)
    zigzag = technicals.rsi(_series([10, 11, 10.5, 12, 11, 13, 12.5, 12, 14, 13] * 4)).dropna()
    assert ((zigzag >= 0) & (zigzag <= 100)).all()
    assert technicals.rsi(_series(range(1, 40))).iloc[:14].isna().all()  # warm-up


def test_rsi_equal_gains_and_losses_is_near_50():
    # Alternating +1/-1 with Wilder smoothing oscillates around 50.
    values = [10 + (i % 2) for i in range(400)]
    assert technicals.rsi(_series(values)).iloc[-1] == pytest.approx(50.0, abs=2.0)


def test_relative_strength_rebased_at_first_shared_date():
    stock = _series([10, 20, 40, 80])
    bench = _series([5, 5, 10], start="2024-01-02")  # starts a day later
    rs = technicals.relative_strength(stock, bench)
    # shared dates: stock 20→40→80 (x4) vs bench 5→5→10 (x2)
    assert rs.tolist() == [1.0, 2.0, 2.0]


@pytest.fixture
def stepped():
    # Daily 2019-06-30 .. 2024-06-30: 100 through 2023-06-30, then 110.
    close = pd.Series(100.0, index=pd.date_range("2019-06-30", "2024-06-30", freq="D"))
    close[close.index > "2023-06-30"] = 110.0
    return close


def test_period_returns(stepped):
    returns = technicals.period_returns(stepped)
    assert returns["1y"] == pytest.approx(0.10)
    assert returns["3y"] == pytest.approx(0.10)
    assert returns["5y"] == pytest.approx(0.10)
    assert returns["ytd"] == pytest.approx(0.0)  # prior year-end close was already 110


def test_period_returns_too_short():
    close = pd.Series(100.0, index=pd.date_range("2024-01-05", "2024-06-30", freq="D"))
    assert technicals.period_returns(close) == {"ytd": None, "1y": None, "3y": None, "5y": None}
    assert technicals.trailing_return(pd.Series(dtype=float), 1) is None


def test_trailing_return_allows_a_weekend_gap_at_the_start():
    close = pd.Series([100.0, 150.0], index=pd.to_datetime(["2023-07-03", "2024-06-30"]))
    assert technicals.trailing_return(close, 1) == pytest.approx(0.5)


def test_max_drawdown():
    close = _series([100, 120, 60, 130, 117])
    assert technicals.max_drawdown(close) == pytest.approx(-0.5)
    assert technicals.max_drawdown(close, window_days=2) == pytest.approx(-0.1)
    assert technicals.max_drawdown(_series([1, 2, 3])) == 0.0
    assert technicals.max_drawdown(pd.Series(dtype=float)) is None


def test_cagr():
    assert technicals.cagr(100, 121, 2) == pytest.approx(0.10)
    assert technicals.cagr(100, 100, 3) == pytest.approx(0.0)
    assert technicals.cagr(-1, 100, 3) is None
    assert technicals.cagr(100, 0, 3) is None
    assert technicals.cagr(100, 121, 0) is None
    assert technicals.cagr(None, 121, 2) is None
