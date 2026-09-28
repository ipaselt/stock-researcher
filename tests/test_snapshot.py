import json
from pathlib import Path

import pytest

from stock_researcher.snapshot import Snapshot, build_snapshot, fields_missing, from_json, safe_div, to_json

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = "2026-09-28"


def _info(ticker):
    return json.loads((FIXTURES / f"{ticker}_info.json").read_text(encoding="utf-8"))


@pytest.fixture
def aapl(fake_provider):
    return build_snapshot(fake_provider, "AAPL", as_of=AS_OF)


def test_safe_div():
    assert safe_div(1, 4) == 0.25
    assert safe_div(None, 4) is None
    assert safe_div(1, None) is None
    assert safe_div(1, 0) is None


def test_aapl_core_fields(aapl):
    info = _info("AAPL")
    assert aapl.meta.ticker == "AAPL" and aapl.meta.as_of == AS_OF
    assert aapl.meta.price == info["currentPrice"]
    assert aapl.valuation.forward_pe == info["forwardPE"]
    assert aapl.valuation.fcf_yield == pytest.approx(info["freeCashflow"] / info["marketCap"])
    assert aapl.valuation.earnings_yield == pytest.approx(1 / info["trailingPE"])
    assert aapl.dividend.dividend_yield == pytest.approx(info["dividendYield"] / 100)
    assert aapl.health.debt_to_equity == pytest.approx(info["debtToEquity"] / 100)
    assert aapl.health.net_debt == pytest.approx(info["totalDebt"] - info["totalCash"])
    assert aapl.analyst.upside_to_target_mean == pytest.approx(info["targetMeanPrice"] / info["currentPrice"] - 1)
    assert aapl.meta.warnings == []


def test_aapl_fields_missing_lists_the_empty_snapshot_fields(aapl):
    # The latest annual Interest Expense is NaN in the fixture, so coverage is the one numeric gap.
    assert aapl.meta.fields_missing == ["health.interest_coverage"]


def test_fields_missing_ignores_unused_fallback_keys(fake_provider, monkeypatch):
    info = _info("AAPL")
    del info["regularMarketPrice"], info["trailingPegRatio"]
    monkeypatch.setattr(fake_provider, "fetch_info", lambda ticker: info)
    snap = build_snapshot(fake_provider, "AAPL", as_of=AS_OF)
    assert snap.meta.price == info["currentPrice"]
    assert snap.meta.fields_missing == ["health.interest_coverage"]


def test_fields_missing_on_empty_snapshot():
    missing = fields_missing(Snapshot())
    assert "meta.price" in missing and "technical.rsi_14" in missing
    assert "meta.name" not in missing and "technical.golden_cross" not in missing  # not float fields


def test_aapl_hand_computed_derived_values(aapl):
    # Literals copied from tests/fixtures/AAPL_* (info, income_stmt, history).
    price = 341.655
    assert aapl.meta.price == price
    assert aapl.profitability.revenue_ttm == 466822987776
    assert aapl.profitability.fcf_margin == pytest.approx(107721875456 / 466822987776)  # 0.2308: TTM over TTM
    assert aapl.health.interest_coverage is None  # latest Interest Expense is NaN in the fixture
    assert aapl.health.cash_to_debt == pytest.approx(62399000576 / 84343996416)
    assert aapl.technical.price_vs_sma200 == pytest.approx(price / 287.71401465 - 1)  # mean of last 200 closes
    assert aapl.technical.pct_from_52w_high == pytest.approx(price / 345.34 - 1)
    span = 1096 / 365.25  # 2022-09-30 to 2025-09-30
    assert aapl.growth.revenue_cagr_3y == pytest.approx((416161e6 / 394328e6) ** (1 / span) - 1)


def test_fcf_margin_falls_back_to_last_fiscal_year_revenue(fake_provider, monkeypatch):
    info = _info("AAPL")
    del info["totalRevenue"]
    monkeypatch.setattr(fake_provider, "fetch_info", lambda ticker: info)
    snap = build_snapshot(fake_provider, "AAPL", as_of=AS_OF)
    assert snap.profitability.revenue_ttm is None
    assert snap.profitability.fcf_margin == pytest.approx(107721875456 / 416161e6)
    assert "profitability.revenue_ttm" in snap.meta.fields_missing


def test_aapl_derived_from_history_and_income(aapl):
    perf, tech, growth = aapl.performance, aapl.technical, aapl.growth
    for value in (perf.return_ytd, perf.return_1y, perf.return_3y, perf.return_5y,
                  perf.spy_return_ytd, perf.spy_return_1y, perf.spy_return_3y, perf.spy_return_5y):
        assert value is not None
    assert perf.rel_1y == pytest.approx(perf.return_1y - perf.spy_return_1y)
    assert perf.rel_3y == pytest.approx(perf.return_3y - perf.spy_return_3y)
    assert -1 <= perf.max_drawdown_1y <= 0
    assert tech.pct_from_52w_high <= 0 <= tech.pct_from_52w_low
    assert 0 <= tech.rsi_14 <= 100
    assert tech.golden_cross == (tech.sma_50 > tech.sma_200)
    assert tech.price_vs_sma50 == pytest.approx(aapl.meta.price / tech.sma_50 - 1)
    assert growth.revenue_cagr_3y is not None and growth.eps_cagr_3y is not None
    assert aapl.profitability.fcf_margin is not None
    assert aapl.events.next_earnings_date == "2026-10-29"
    assert 0 < len(aapl.events.news) <= 10
    assert all(item["title"] and item["url"] for item in aapl.events.news)


def test_json_round_trip(aapl):
    text = to_json(aapl)
    assert list(json.loads(text)) == ["meta", "valuation", "growth", "profitability", "health", "performance",
                                      "dividend", "analyst", "technical", "ownership", "events"]
    assert from_json(text) == aapl
    assert "NaN" not in text


def test_json_round_trip_empty():
    assert from_json(to_json(Snapshot())) == Snapshot()


def test_negative_eps_company(fake_provider):
    snap = build_snapshot(fake_provider, "RIVN", as_of=AS_OF)
    assert snap.valuation.trailing_eps < 0 and snap.valuation.forward_pe < 0
    assert snap.valuation.trailing_pe is None and snap.valuation.earnings_yield is None
    assert snap.growth.eps_cagr_3y is None  # negative EPS has no CAGR
    assert snap.growth.net_income_cagr_3y is None
    assert any("negative forward earnings" in w for w in snap.meta.warnings)
    assert from_json(to_json(snap)) == snap


def test_sparse_otc_company(fake_provider):
    snap = build_snapshot(fake_provider, "HCMC", as_of=AS_OF)
    assert snap.meta.price is not None
    assert len(snap.meta.fields_missing) >= 10
    assert "valuation.trailing_pe" in snap.meta.fields_missing  # Yahoo sent the string "Infinity"
    assert any("trailingPE" in w for w in snap.meta.warnings)
    assert snap.valuation.trailing_pe is None
    assert snap.events.news == [] and snap.events.next_earnings_date is None
    assert snap.analyst.target_mean is None
    assert from_json(to_json(snap)) == snap
