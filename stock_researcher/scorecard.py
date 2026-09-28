"""The weighted scorecard: a long-term quality-at-a-reasonable-price lens over the Snapshot.

Every metric, weight and band edge lives in the one `METRICS` table below; `grade()` is the only grading
function. Ratios are fractions (0.25 = 25%), multiples are raw (15 = 15x).

Band convention. Each metric has four ordered thresholds (the A, B, C and D edges):
- higher_is_better=True:  value >= A -> A, >= B -> B, >= C -> C, >= D -> D, else F.
- higher_is_better=False: value <= A -> A, <= B -> B, <= C -> C, <= D -> D, else F.
A value exactly on a threshold takes the BETTER grade (forward P/E of exactly 15 is an A, not a B).

`technical.price_vs_sma200` is non-monotonic: A is the middle band (0 to +20% above the 200-day average).
It is modelled as a higher-is-better ladder (0 / -5% / -15% / -25%) plus an `a_cap` of +20%: a price more
than 20% above the average is extended and grades B instead of A.

Special cases (checked in this order, each documented and tested):
1. `debt_to_equity` < 0 (negative shareholders' equity, e.g. buyback-driven) -> skipped, note "negative
   equity"; the ratio has no meaningful reading, so it neither rewards nor punishes.
2. `total_debt` known and <= 0 -> `cash_to_debt` and `interest_coverage` grade A, note "no meaningful debt".
3. `interest_coverage` None while debt > 0 -> skipped, note "no reported interest expense".
4. Any other None -> skipped, note "missing".
5. `forward_pe`, `peg`, `ev_ebitda` <= 0 -> F, note "negative or zero" (negative earnings / growth / EBITDA).
6. `interest_coverage` < 0 (negative EBIT) -> F, note "negative EBIT".

Math: points = GRADE_POINTS[grade]; a category score is sum(points/10 * weight) / covered weight * 100 over
its covered metrics; the total is the same over all covered metrics, rounded to 1 decimal; `coverage_pct` is
the covered weight / 100. Skipped metrics drop out and the rest renormalize. `band_word` is read off the
rounded total, so the printed number is the number that decides.
"""
import math
from dataclasses import dataclass

GRADE_POINTS = {"A": 10, "B": 7.5, "C": 5, "D": 2.5, "F": 0}
GRADES = ("A", "B", "C", "D")


@dataclass(frozen=True)
class Metric:
    category: str
    field: str  # snapshot path "group.field"
    weight: int
    bands: tuple[float, float, float, float]  # A, B, C, D edges
    higher_is_better: bool
    note: str
    a_cap: float | None = None  # non-monotonic: above this an A drops to B


METRICS = [
    # valuation (30)
    Metric("valuation", "valuation.forward_pe", 10, (15, 22, 30, 45), False, "forward P/E, x"),
    Metric("valuation", "valuation.peg", 8, (1.0, 1.5, 2.5, 4.0), False, "PEG, x"),
    Metric("valuation", "valuation.ev_ebitda", 6, (10, 15, 22, 30), False, "EV/EBITDA, x"),
    Metric("valuation", "valuation.fcf_yield", 6, (0.06, 0.04, 0.025, 0.01), True, "FCF / market cap"),
    # growth (20)
    Metric("growth", "growth.revenue_growth_yoy", 6, (0.20, 0.12, 0.06, 0.0), True, "revenue growth yoy"),
    Metric("growth", "growth.revenue_cagr_3y", 6, (0.15, 0.10, 0.05, 0.0), True, "revenue CAGR 3y"),
    Metric("growth", "growth.earnings_growth_yoy", 4, (0.20, 0.10, 0.03, -0.10), True, "earnings growth yoy"),
    Metric("growth", "growth.eps_cagr_3y", 4, (0.15, 0.10, 0.05, 0.0), True, "diluted EPS CAGR 3y"),
    # profitability (20)
    Metric("profitability", "profitability.gross_margin", 4, (0.55, 0.40, 0.30, 0.20), True, "gross margin"),
    Metric("profitability", "profitability.operating_margin", 6, (0.25, 0.15, 0.10, 0.05), True, "operating margin"),
    Metric("profitability", "profitability.roe", 6, (0.25, 0.15, 0.10, 0.05), True, "return on equity"),
    Metric("profitability", "profitability.fcf_margin", 4, (0.20, 0.12, 0.06, 0.0), True, "FCF / revenue (TTM)"),
    # health (20)
    Metric("health", "health.debt_to_equity", 6, (0.3, 0.7, 1.2, 2.0), False, "debt / equity, x"),
    Metric("health", "health.current_ratio", 4, (2.0, 1.5, 1.0, 0.8), True, "current ratio, x"),
    Metric("health", "health.interest_coverage", 6, (15, 8, 4, 1.5), True, "EBIT / interest expense, x"),
    Metric("health", "health.cash_to_debt", 4, (1.0, 0.5, 0.25, 0.1), True, "cash / total debt, x"),
    # momentum (10)
    Metric("momentum", "performance.rel_1y", 5, (0.15, 0.05, -0.05, -0.15), True, "1y return minus SPY 1y"),
    Metric("momentum", "technical.price_vs_sma200", 5, (0.0, -0.05, -0.15, -0.25), True,
           "price / SMA200 - 1; A is 0 to +20%, above +20% is B", a_cap=0.20),
]

CATEGORY_WEIGHTS: dict[str, int] = {}  # derived from METRICS so the table stays the one source
for _m in METRICS:
    CATEGORY_WEIGHTS[_m.category] = CATEGORY_WEIGHTS.get(_m.category, 0) + _m.weight

NONPOSITIVE_IS_F = {"valuation.forward_pe", "valuation.peg", "valuation.ev_ebitda"}
DEBT_FREE_A = {"health.cash_to_debt", "health.interest_coverage"}


@dataclass
class MetricResult:
    field: str
    category: str
    value: float | None
    grade: str | None
    points: float | None
    weight: int
    covered: bool
    note: str | None = None


@dataclass
class CategoryScore:
    score: float | None  # 0-100 over covered weight; None when nothing in the category is covered
    coverage: float  # covered weight / category weight


@dataclass
class ScoreResult:
    total: float | None
    band_word: str | None
    coverage_pct: float
    categories: dict[str, CategoryScore]
    metrics: list[MetricResult]


def grade(metric: Metric, value: float) -> str:
    """Letter grade for a finite value by the metric's ordered thresholds (on a threshold -> better grade)."""
    if metric.a_cap is not None and value > metric.a_cap:
        return "B"
    for letter, edge in zip(GRADES, metric.bands):
        if (value >= edge) if metric.higher_is_better else (value <= edge):
            return letter
    return "F"


def _value(snapshot, path: str) -> float | None:
    group, name = path.split(".")
    value = getattr(getattr(snapshot, group), name)
    if value is None or isinstance(value, bool):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _score_metric(metric: Metric, snapshot) -> MetricResult:
    value = _value(snapshot, metric.field)
    total_debt = _value(snapshot, "health.total_debt")

    def result(letter, note=None):
        covered = letter is not None
        points = GRADE_POINTS[letter] if covered else None
        return MetricResult(metric.field, metric.category, value, letter, points, metric.weight, covered, note)

    if metric.field == "health.debt_to_equity" and value is not None and value < 0:
        return result(None, "negative equity")
    if metric.field in DEBT_FREE_A and total_debt is not None and total_debt <= 0:
        return result("A", "no meaningful debt")
    if value is None:
        if metric.field == "health.interest_coverage" and total_debt is not None and total_debt > 0:
            return result(None, "no reported interest expense")
        return result(None, "missing")
    if metric.field in NONPOSITIVE_IS_F and value <= 0:
        return result("F", "negative or zero")
    if metric.field == "health.interest_coverage" and value < 0:
        return result("F", "negative EBIT")
    return result(grade(metric, value))


def _weighted(results: list[MetricResult]) -> tuple[float | None, int]:
    """(0-100 score over the covered metrics, covered weight)."""
    covered = [r for r in results if r.covered]
    weight = sum(r.weight for r in covered)
    if weight == 0:
        return None, 0
    return sum(r.points / 10 * r.weight for r in covered) / weight * 100, weight


def band_word(total: float | None) -> str | None:
    if total is None:
        return None
    if total >= 75:
        return "strong"
    if total >= 60:
        return "good"
    if total >= 45:
        return "mixed"
    return "weak"


def score_snapshot(snapshot) -> ScoreResult:
    metrics = [_score_metric(m, snapshot) for m in METRICS]
    categories = {}
    for name, cat_weight in CATEGORY_WEIGHTS.items():
        score, weight = _weighted([r for r in metrics if r.category == name])
        categories[name] = CategoryScore(None if score is None else round(score, 1), weight / cat_weight)
    total, weight = _weighted(metrics)
    total = None if total is None else round(total, 1)
    return ScoreResult(total, band_word(total), weight / 100, categories, metrics)
