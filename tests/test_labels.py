"""One test per rule L1-L8 (and L5b) whose inputs fail every earlier rule, plus precedence tests.

Baseline (-> L8 WAIT): score 70, coverage 100%, health 80, fair value 100 (entry 85, high band ~115), price 95,
30% below the 52-week high, 1y return 0%.
"""
import pytest

from stock_researcher.fair_value import FairValue, compute_fair_value
from stock_researcher.labels import suggest_label
from stock_researcher.scorecard import CategoryScore, ScoreResult, band_word
from stock_researcher.snapshot import Snapshot


def _case(total=70.0, coverage=1.0, health=80.0, fair_value=100.0, mos=0.15, price=95.0,
          from_high=-0.30, ret_1y=0.0, sanity=None):
    score = ScoreResult(total, band_word(total), coverage,
                        {"health": CategoryScore(health, 0.0 if health is None else 1.0)}, [])
    if fair_value is None:
        fv = FairValue(-1.0, 20, "sector_default", 0, None, None, None, mos, None, None,
                       "forward EPS -1.00 <= 0")
    else:
        fv = FairValue(fair_value / 20, 20, "sector_default", 0, fair_value, fair_value * 0.85, fair_value * 1.15,
                       mos, fair_value * (1 - mos), None, None, sanity)
    snap = Snapshot()
    snap.meta.price = price
    snap.technical.pct_from_52w_high = from_high
    snap.performance.return_1y = ret_1y
    return suggest_label(score, fv, snap)


def test_baseline_is_l8_wait():
    s = _case()
    assert (s.label, s.rule_id) == ("WAIT", "L8")
    assert s.entry_target == pytest.approx(85)
    assert "95.00" in s.reason and "85.00" in s.reason


@pytest.mark.parametrize("coverage", [0.59, 0.0])
def test_l1_low_coverage(coverage):
    s = _case(coverage=coverage)
    assert (s.label, s.rule_id, s.entry_target) == ("NOT LOOKING", "L1", None)
    assert s.reason == f"insufficient data (coverage {coverage:.0%})"


def test_l1_no_total():
    s = _case(total=None, coverage=0.0, health=None)
    assert (s.label, s.rule_id) == ("NOT LOOKING", "L1")


def test_l1_boundary_60_percent_passes():
    assert _case(coverage=0.60).rule_id == "L8"


def test_l2_health_fail():
    s = _case(health=29.9)
    assert (s.label, s.rule_id) == ("NOT LOOKING", "L2")
    assert "29.9" in s.reason and "balance-sheet fail" in s.reason


def test_l2_boundary_and_uncovered_health():
    assert _case(health=30.0).rule_id == "L8"
    assert _case(health=None).rule_id == "L8"


def test_l3_sell():
    s = _case(total=44.9, price=115.01)
    assert (s.label, s.rule_id, s.entry_target) == ("SELL", "L3", None)
    assert "44.9" in s.reason and "115.01" in s.reason and "115.00" in s.reason


def test_l4_low_score():
    s = _case(total=54.9)
    assert (s.label, s.rule_id) == ("NOT LOOKING", "L4")
    assert "54.9" in s.reason


def test_l4_boundary_55_passes():
    assert _case(total=55.0).rule_id == "L8"


def test_l5_no_fair_value():
    s = _case(fair_value=None)
    assert (s.label, s.rule_id, s.entry_target) == ("NOT LOOKING", "L5", None)
    assert s.reason == "no fair value (forward EPS -1.00 <= 0); planner may override for growth names"


@pytest.mark.parametrize("price", [85.0, 60.0])
def test_l6_buy_at_or_below_entry(price):
    s = _case(price=price)
    assert (s.label, s.rule_id) == ("BUY", "L6")
    assert s.entry_target == pytest.approx(85)
    assert f"price {price:.2f} <= entry 85.00" == s.reason


@pytest.mark.parametrize("from_high, ret_1y", [(-0.05, 0.0), (0.0, None), (-0.30, 0.40), (None, 0.55)])
def test_l7_has_run(from_high, ret_1y):
    s = _case(price=115.01, from_high=from_high, ret_1y=ret_1y)
    assert (s.label, s.rule_id) == ("HAS RUN", "L7")
    assert s.entry_target == pytest.approx(85)
    assert "115.01" in s.reason


@pytest.mark.parametrize("price, from_high, ret_1y", [
    (114.99, -0.01, 0.9),    # just under the high band
    (130.0, -0.051, 0.399),  # above the band but neither momentum condition holds
    (130.0, None, None),     # above the band, momentum unknown
    (85.01, -0.01, 0.9),     # just above entry
])
def test_l8_wait(price, from_high, ret_1y):
    s = _case(price=price, from_high=from_high, ret_1y=ret_1y)
    assert (s.label, s.rule_id) == ("WAIT", "L8")
    assert s.entry_target == pytest.approx(85)


def test_l8_missing_price():
    s = _case(price=None)
    assert (s.label, s.rule_id) == ("WAIT", "L8") and "price unavailable" in s.reason


# --- precedence ---

def test_l1_beats_l6():
    assert _case(coverage=0.5, price=50.0).rule_id == "L1"


def test_l1_beats_l2():
    assert _case(coverage=0.5, health=10.0).rule_id == "L1"


def test_l2_beats_l3():
    assert _case(health=10.0, total=30.0, price=200.0).rule_id == "L2"


def test_l3_beats_l4():
    assert _case(total=40.0, price=120.0).rule_id == "L3"


def test_l4_when_low_score_but_not_above_band():
    assert _case(total=40.0, price=114.99).rule_id == "L4"


def test_l4_beats_l5():
    assert _case(total=50.0, fair_value=None).rule_id == "L4"


def test_l3_needs_fair_value():
    assert _case(total=40.0, fair_value=None, price=500.0).rule_id == "L4"


def test_l6_beats_l7_momentum():
    # L6 and L7 cannot overlap on price (entry < fair value < high band); momentum never blocks a BUY.
    assert _case(price=80.0, from_high=0.0, ret_1y=1.0).rule_id == "L6"


# --- boundaries ---

def test_price_equal_to_band_high_triggers_neither_l3_nor_l7():
    score = ScoreResult(40.0, "weak", 1.0, {"health": CategoryScore(80.0, 1.0)}, [])
    fv = FairValue(5.0, 20, "sector_default", 0, 100.0, 85.0, 115.0, 0.15, 85.0, None, None)
    snap = Snapshot()
    snap.meta.price = 115.0
    snap.technical.pct_from_52w_high = 0.0
    snap.performance.return_1y = 1.0
    assert suggest_label(score, fv, snap).rule_id == "L4"  # not L3
    score.total = 70.0
    assert suggest_label(score, fv, snap).rule_id == "L8"  # not L7


def test_total_exactly_45_above_band_is_l4_not_l3():
    s = _case(total=45.0, price=200.0)
    assert (s.label, s.rule_id) == ("NOT LOOKING", "L4")


# --- L5b: fair value not trusted ---

SANITY = "fair value 723.66 (fair_value.fair_value) is above the highest analyst target 515.00 (analyst.target_high)"


def test_l5b_untrusted_fair_value_is_wait_without_target():
    s = _case(sanity=SANITY)
    assert (s.label, s.rule_id, s.entry_target) == ("WAIT", "L5b", None)
    assert s.reason == f"fair value not trusted: {SANITY}; no entry target (planner may cite one)"


def test_l5b_needs_sanity_set():
    assert _case(sanity=None).rule_id == "L8"
    assert _case(sanity="").rule_id == "L8"


@pytest.mark.parametrize("kwargs, rule", [
    (dict(coverage=0.5), "L1"), (dict(health=10.0), "L2"), (dict(total=40.0, price=120.0), "L3"),
    (dict(total=50.0), "L4"), (dict(fair_value=None), "L5"),
])
def test_earlier_rules_beat_l5b(kwargs, rule):
    assert _case(sanity=SANITY, **kwargs).rule_id == rule


@pytest.mark.parametrize("price", [85.0, 60.0])
def test_l5b_beats_l6(price):
    assert _case(price=price).rule_id == "L6"
    assert _case(price=price, sanity=SANITY).rule_id == "L5b"


def test_l5b_beats_l7():
    assert _case(price=115.01, from_high=0.0).rule_id == "L7"
    assert _case(price=115.01, from_high=0.0, sanity=SANITY).rule_id == "L5b"


def test_l5b_with_missing_price():
    assert _case(price=None, sanity=SANITY).rule_id == "L5b"


def test_nvda_golden_is_l5b_not_l6():
    # the NVDA run 2026-09-28: the rule said BUY (L6) on a 723.66 fair value; the planner overrode it by hand
    snap = Snapshot()
    snap.meta.price, snap.meta.sector = 229.61, "Technology"
    snap.valuation.forward_eps, snap.valuation.fiscal_year_pe = 15.68, [723.66 / 15.68] * 3
    snap.valuation.forward_pe, snap.analyst.target_high = 14.64, 515.0
    snap.technical.pct_from_52w_high, snap.performance.return_1y = -0.02, 0.5
    score = ScoreResult(87.2, band_word(87.2), 1.0, {"health": CategoryScore(90.0, 1.0)}, [])
    fv = compute_fair_value(snap, score.total)
    assert fv.fair_value == pytest.approx(723.66) and fv.entry_price == pytest.approx(687.477, abs=1e-3)
    s = suggest_label(score, fv, snap)
    assert (s.label, s.rule_id, s.entry_target) == ("WAIT", "L5b", None)
    assert "723.66" in s.reason and "analyst.target_high" in s.reason
