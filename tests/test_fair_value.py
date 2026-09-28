import pandas as pd
import pytest

from stock_researcher.fair_value import DEFAULT_PE, SECTOR_DEFAULT_PE, compute_fair_value, margin_of_safety, median_pe
from stock_researcher.snapshot import Snapshot, fiscal_year_pe


def historical_median_pe(close, income):
    return median_pe(fiscal_year_pe(close, income))


def _snapshot(eps=10.0, pes=None, sector="Technology", price=200.0) -> Snapshot:
    snap = Snapshot()
    snap.valuation.forward_eps = eps
    snap.valuation.fiscal_year_pe = pes
    snap.meta.sector = sector
    snap.meta.price = price
    return snap


def _income(eps_by_date: dict) -> pd.DataFrame:
    return pd.DataFrame({pd.Timestamp(d): [e] for d, e in eps_by_date.items()}, index=["Diluted EPS"])


def test_median_of_five_years():
    fv = compute_fair_value(_snapshot(pes=[30, 10, 20, 50, 40]), 80)
    assert (fv.fair_pe, fv.fair_pe_source, fv.n_years) == (30, "historical_median", 5)
    assert fv.fair_value == pytest.approx(300)


def test_median_of_three_years():
    fv = compute_fair_value(_snapshot(pes=[22, 18, 30]), 80)
    assert (fv.fair_pe, fv.fair_pe_source, fv.n_years) == (22, "historical_median", 3)


def test_two_years_falls_back_to_sector_default():
    fv = compute_fair_value(_snapshot(pes=[22, 18], sector="Energy"), 80)
    assert (fv.fair_pe, fv.fair_pe_source, fv.n_years) == (SECTOR_DEFAULT_PE["Energy"], "sector_default", 2)
    assert fv.fair_value == pytest.approx(10 * 12)


def test_no_history_falls_back_to_sector_default():
    fv = compute_fair_value(_snapshot(pes=None), 80)
    assert (fv.fair_pe, fv.fair_pe_source, fv.n_years) == (25, "sector_default", 0)


@pytest.mark.parametrize("sector", ["Crypto Things", None])
def test_unknown_sector_uses_18(sector):
    fv = compute_fair_value(_snapshot(pes=[], sector=sector), 80)
    assert fv.fair_pe == DEFAULT_PE == 18 and fv.fair_pe_source == "sector_default"


def test_median_uses_at_most_five_most_recent_years():
    assert median_pe([10, 10, 10, 10, 10, 99, 99, 99]) == (10, 5)


def test_median_ignores_unusable_values():
    assert median_pe([20, -5, 0, float("nan"), 30]) == (None, 2)
    assert median_pe(None) == (None, 0)


def test_historical_median_pe_from_history_and_income():
    close = pd.Series([50.0, 100.0, 120.0, 90.0, 200.0],
                      index=pd.to_datetime(["2021-12-31", "2022-12-30", "2023-12-29", "2024-12-31", "2025-12-31"]))
    income = _income({"2025-12-31": 10.0, "2024-12-31": 3.0, "2023-12-31": 6.0, "2022-12-31": 4.0,
                      "2021-12-31": -1.0})
    # 2025: 200/10=20, 2024: 90/3=30, 2023: 120/6=20 (Dec 31 is a Sunday -> the Dec 29 close), 2022: 100/4=25
    assert historical_median_pe(close, income) == (22.5, 4)


@pytest.mark.parametrize("years, expected", [(5, (20.0, 5)), (3, (20.0, 3)), (2, (None, 2))])
def test_historical_median_pe_year_counts(years, expected):
    dates = pd.date_range("2021-12-31", periods=5, freq="YE")
    close = pd.Series(100.0, index=dates)
    income = _income({d: (5.0 if i < years else float("nan")) for i, d in enumerate(reversed(dates))})
    assert historical_median_pe(close, income) == expected


@pytest.mark.parametrize("eps, reason", [(None, "forward EPS missing"), (float("nan"), "forward EPS missing"),
                                         (0.0, "forward EPS 0.00 <= 0"), (-1.5, "forward EPS -1.50 <= 0")])
def test_nonpositive_or_missing_forward_eps_has_no_fair_value(eps, reason):
    fv = compute_fair_value(_snapshot(eps=eps, pes=[20, 20, 20]), 80)
    assert fv.fair_value is None and fv.entry_price is None and fv.upside is None
    assert fv.band_low is None and fv.band_high is None
    assert fv.reason == reason


def test_earnings_yield_exactly_1pct_is_computed():
    fv = compute_fair_value(_snapshot(eps=1.0, pes=[20, 20, 20], price=100.0), 80)  # forward P/E exactly 100
    assert fv.fair_value == pytest.approx(20) and fv.reason is None


def test_earnings_yield_below_1pct_has_no_fair_value():
    fv = compute_fair_value(_snapshot(eps=0.999, pes=[20, 20, 20], price=100.0), 80)
    assert fv.fair_value is None and fv.entry_price is None
    assert fv.reason == ("forward earnings yield 1.00% below 1% (forward P/E > 100): "
                         "earnings-based fair value not meaningful")
    fv = compute_fair_value(_snapshot(eps=0.5, pes=[20, 20, 20], price=100.0), 80)
    assert fv.reason.startswith("forward earnings yield 0.50% below 1%")


def test_earnings_yield_floor_skipped_without_price():
    fv = compute_fair_value(_snapshot(eps=0.01, pes=[20, 20, 20], price=None), 80)
    assert fv.fair_value == pytest.approx(0.2) and fv.upside is None


@pytest.mark.parametrize("score, mos", [(100, 0.05), (75, 0.05), (74.9, 0.15), (60, 0.15), (59.9, 0.20),
                                        (0, 0.20), (None, 0.20)])
def test_margin_of_safety_tiers(score, mos):
    assert margin_of_safety(score) == mos
    assert compute_fair_value(_snapshot(pes=[20, 20, 20]), score).margin_of_safety == mos


def test_band_entry_and_upside_arithmetic():
    fv = compute_fair_value(_snapshot(eps=10.0, pes=[20, 20, 20], price=160.0), 80)
    assert fv.fair_value == pytest.approx(200)
    assert fv.band_low == pytest.approx(170) and fv.band_high == pytest.approx(230)  # the band is always +/-15%
    assert fv.entry_price == pytest.approx(190)  # 200 x (1 - 0.05): the entry uses the margin of safety
    assert compute_fair_value(_snapshot(eps=10.0, pes=[20, 20, 20]), 50).entry_price == pytest.approx(160)
    assert fv.upside == pytest.approx(200 / 160 - 1)
    assert fv.reason is None


def test_missing_price_has_no_upside():
    fv = compute_fair_value(_snapshot(price=None, pes=[20, 20, 20]), 65)
    assert fv.fair_value == pytest.approx(200) and fv.upside is None
