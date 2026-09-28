import pytest

from stock_researcher.scorecard import CATEGORY_WEIGHTS, GRADE_POINTS, METRICS, band_word, grade, score_snapshot
from stock_researcher.snapshot import Snapshot

MONOTONIC = [m for m in METRICS if m.a_cap is None]
SMA200 = next(m for m in METRICS if m.field == "technical.price_vs_sma200")
EPS = 1e-9


def _set(snap, path, value):
    group, name = path.split(".")
    setattr(getattr(snap, group), name, value)


def _snapshot(values: dict, total_debt=1e9) -> Snapshot:
    snap = Snapshot()
    snap.health.total_debt = total_debt
    for path, value in values.items():
        _set(snap, path, value)
    return snap


def _all_a() -> dict:
    return {m.field: m.bands[0] for m in METRICS}  # exactly on the A edge -> A


def _all_f() -> dict:
    return {m.field: m.bands[3] + (-1 if m.higher_is_better else 100) for m in METRICS}


def _metric(result, field):
    return next(r for r in result.metrics if r.field == field)


# The approved plan table, pinned literally: (category, field, weight, A, B, C, D, higher_is_better, a_cap).
GOLDEN = [
    ("valuation", "valuation.forward_pe", 10, 15, 22, 30, 45, False, None),
    ("valuation", "valuation.peg", 8, 1.0, 1.5, 2.5, 4.0, False, None),
    ("valuation", "valuation.ev_ebitda", 6, 10, 15, 22, 30, False, None),
    ("valuation", "valuation.fcf_yield", 6, 0.06, 0.04, 0.025, 0.01, True, None),
    ("growth", "growth.revenue_growth_yoy", 6, 0.20, 0.12, 0.06, 0.0, True, None),
    ("growth", "growth.revenue_cagr_3y", 6, 0.15, 0.10, 0.05, 0.0, True, None),
    ("growth", "growth.earnings_growth_yoy", 4, 0.20, 0.10, 0.03, -0.10, True, None),
    ("growth", "growth.eps_cagr_3y", 4, 0.15, 0.10, 0.05, 0.0, True, None),
    ("profitability", "profitability.gross_margin", 4, 0.55, 0.40, 0.30, 0.20, True, None),
    ("profitability", "profitability.operating_margin", 6, 0.25, 0.15, 0.10, 0.05, True, None),
    ("profitability", "profitability.roe", 6, 0.25, 0.15, 0.10, 0.05, True, None),
    ("profitability", "profitability.fcf_margin", 4, 0.20, 0.12, 0.06, 0.0, True, None),
    ("health", "health.debt_to_equity", 6, 0.3, 0.7, 1.2, 2.0, False, None),
    ("health", "health.current_ratio", 4, 2.0, 1.5, 1.0, 0.8, True, None),
    ("health", "health.interest_coverage", 6, 15, 8, 4, 1.5, True, None),
    ("health", "health.cash_to_debt", 4, 1.0, 0.5, 0.25, 0.1, True, None),
    ("momentum", "performance.rel_1y", 5, 0.15, 0.05, -0.05, -0.15, True, None),
    ("momentum", "technical.price_vs_sma200", 5, 0.0, -0.05, -0.15, -0.25, True, 0.20),
]


def test_metrics_match_the_golden_plan_table():
    actual = [(m.category, m.field, m.weight, *m.bands, m.higher_is_better, m.a_cap) for m in METRICS]
    assert actual == GOLDEN


def test_weights_sum_to_100():
    assert sum(m.weight for m in METRICS) == 100
    assert CATEGORY_WEIGHTS == {"valuation": 30, "growth": 20, "profitability": 20, "health": 20, "momentum": 10}
    assert len({m.field for m in METRICS}) == len(METRICS)


def test_every_metric_field_exists_on_the_snapshot():
    snap = Snapshot()
    for m in METRICS:
        group, name = m.field.split(".")
        assert hasattr(getattr(snap, group), name), m.field


def test_all_a_scores_100():
    result = score_snapshot(_snapshot(_all_a()))
    assert result.total == 100.0 and result.band_word == "strong" and result.coverage_pct == 1.0
    assert all(r.grade == "A" and r.points == 10 for r in result.metrics)
    assert all(c.score == 100.0 and c.coverage == 1.0 for c in result.categories.values())


def test_all_f_scores_0():
    result = score_snapshot(_snapshot(_all_f()))
    assert result.total == 0.0 and result.band_word == "weak" and result.coverage_pct == 1.0
    assert all(r.grade == "F" and r.points == 0 for r in result.metrics)


def test_one_f_metric_costs_its_weight():
    values = _all_a() | {"valuation.forward_pe": 100}  # weight 10 -> F
    result = score_snapshot(_snapshot(values))
    assert result.total == 90.0
    assert result.categories["valuation"].score == pytest.approx(round(20 / 30 * 100, 1))


def test_missing_metric_renormalizes_and_drops_coverage_by_its_weight():
    values = _all_a() | {"valuation.forward_pe": 100}
    values.pop("valuation.forward_pe")  # None: the F drops out and the rest renormalize
    result = score_snapshot(_snapshot(values))
    assert result.total == 100.0
    assert result.coverage_pct == pytest.approx(0.90)
    assert result.categories["valuation"].coverage == pytest.approx(20 / 30)
    fpe = _metric(result, "valuation.forward_pe")
    assert not fpe.covered and fpe.grade is None and fpe.points is None and fpe.note == "missing"


def test_renormalized_total_is_weighted_mean_of_covered():
    # forward_pe (10) B, peg (8) D, everything else missing -> (7.5*10 + 2.5*8) / 18 * 10
    result = score_snapshot(_snapshot({"valuation.forward_pe": 20, "valuation.peg": 3.0}))
    assert result.total == round((7.5 * 10 + 2.5 * 8) / 18 * 10, 1)
    assert result.coverage_pct == pytest.approx(0.18)
    assert result.categories["growth"].score is None and result.categories["growth"].coverage == 0


def test_nothing_covered_total_none():
    result = score_snapshot(Snapshot())
    assert result.total is None and result.band_word is None and result.coverage_pct == 0
    assert all(c.score is None and c.coverage == 0 for c in result.categories.values())


@pytest.mark.parametrize("total, word", [(100, "strong"), (75, "strong"), (74.9, "good"), (60, "good"),
                                         (59.9, "mixed"), (45, "mixed"), (44.9, "weak"), (0, "weak")])
def test_band_word(total, word):
    assert band_word(total) == word


# --- parametrized band edges: on a threshold -> the better grade; just past it -> the next grade ---

EDGE_CASES = []
for _m in MONOTONIC:
    _worse = -EPS if _m.higher_is_better else EPS
    for _i, _edge in enumerate(_m.bands):
        _better, _next = "ABCD"[_i], "BCDF"[_i]
        EDGE_CASES.append(pytest.param(_m, _edge, _better, id=f"{_m.field}-on-{_better}"))
        EDGE_CASES.append(pytest.param(_m, _edge + _worse, _next, id=f"{_m.field}-past-{_better}"))


@pytest.mark.parametrize("metric, value, expected", EDGE_CASES)
def test_band_edges(metric, value, expected):
    assert grade(metric, value) == expected


@pytest.mark.parametrize("metric", MONOTONIC, ids=lambda m: m.field)
def test_band_interiors(metric):
    """A value in the middle of each band gets that band's grade."""
    a, b, c, d = metric.bands
    step = 1 if metric.higher_is_better else -1
    beyond_a = a + step * abs(a - b)
    beyond_d = d - step * abs(c - d)
    for value, expected in [(beyond_a, "A"), ((a + b) / 2, "B"), ((b + c) / 2, "C"), ((c + d) / 2, "D"),
                            (beyond_d, "F")]:
        assert grade(metric, value) == expected, (value, expected)


def test_bands_are_ordered():
    for m in METRICS:
        ordered = sorted(m.bands, reverse=m.higher_is_better)
        assert list(m.bands) == ordered, m.field


@pytest.mark.parametrize("value, expected", [
    (0.50, "B"), (0.20 + EPS, "B"), (0.20, "A"), (0.10, "A"), (0.0, "A"),
    (-EPS, "B"), (-0.05, "B"), (-0.05 - EPS, "C"), (-0.15, "C"), (-0.15 - EPS, "D"),
    (-0.25, "D"), (-0.25 - EPS, "F"), (-0.60, "F"),
])
def test_price_vs_sma200_is_non_monotonic(value, expected):
    assert grade(SMA200, value) == expected


# --- special cases ---

@pytest.mark.parametrize("field", ["valuation.forward_pe", "valuation.peg", "valuation.ev_ebitda"])
@pytest.mark.parametrize("value", [0.0, -5.0])
def test_nonpositive_valuation_multiple_is_f(field, value):
    r = _metric(score_snapshot(_snapshot({field: value})), field)
    assert r.grade == "F" and r.covered and r.note == "negative or zero"


def test_small_positive_valuation_multiple_is_a():
    r = _metric(score_snapshot(_snapshot({"valuation.forward_pe": 0.5})), "valuation.forward_pe")
    assert r.grade == "A" and r.note is None


@pytest.mark.parametrize("total_debt", [0.0, -1.0])
def test_zero_debt_grades_both_debt_metrics_a(total_debt):
    # cash_to_debt / interest_coverage are None when there is no debt; they grade A, not "missing".
    result = score_snapshot(_snapshot({"health.cash_to_debt": None, "health.interest_coverage": None},
                                      total_debt=total_debt))
    for field in ("health.cash_to_debt", "health.interest_coverage"):
        r = _metric(result, field)
        assert r.grade == "A" and r.covered and r.note == "no meaningful debt"


def test_interest_coverage_none_with_debt_is_uncovered_with_note():
    values = _all_a()
    values.pop("health.interest_coverage")
    result = score_snapshot(_snapshot(values, total_debt=5e9))
    r = _metric(result, "health.interest_coverage")
    assert not r.covered and r.grade is None and r.note == "no reported interest expense"
    assert result.coverage_pct == pytest.approx(0.94)
    assert result.categories["health"].coverage == pytest.approx(14 / 20)


def test_interest_coverage_none_with_unknown_debt_is_missing():
    r = _metric(score_snapshot(_snapshot({}, total_debt=None)), "health.interest_coverage")
    assert not r.covered and r.note == "missing"


def test_negative_interest_coverage_is_f():
    r = _metric(score_snapshot(_snapshot({"health.interest_coverage": -3.0})), "health.interest_coverage")
    assert r.grade == "F" and r.covered and r.note == "negative EBIT"


def test_negative_debt_to_equity_is_uncovered():
    r = _metric(score_snapshot(_snapshot({"health.debt_to_equity": -2.5})), "health.debt_to_equity")
    assert not r.covered and r.grade is None and r.note == "negative equity"


def test_points_follow_grade_points():
    result = score_snapshot(_snapshot({"valuation.forward_pe": 25}))  # C
    r = _metric(result, "valuation.forward_pe")
    assert r.grade == "C" and r.points == GRADE_POINTS["C"] == 5 and r.weight == 10 and r.value == 25


def test_zero_debt_to_equity_is_a_and_covered():
    r = _metric(score_snapshot(_snapshot({"health.debt_to_equity": 0.0})), "health.debt_to_equity")
    assert r.grade == "A" and r.covered and r.note is None


def test_negative_equity_skip_only_below_zero():
    r = _metric(score_snapshot(_snapshot({"health.debt_to_equity": -1e-9})), "health.debt_to_equity")
    assert not r.covered and r.note == "negative equity"
