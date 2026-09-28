"""docs/ = code: every number the methodology pages state is checked against the module that uses it."""
from pathlib import Path

import pytest

from stock_researcher import fair_value, labels
from stock_researcher.report import MULTIPLES
from stock_researcher.scorecard import CATEGORY_WEIGHTS, GRADE_POINTS, METRICS

DOCS = Path(__file__).parent.parent / "docs"
SCORECARD = (DOCS / "scorecard.md").read_text(encoding="utf-8")
FAIR_VALUE = (DOCS / "fair-value.md").read_text(encoding="utf-8")
LABELS = (DOCS / "labels.md").read_text(encoding="utf-8")


def pct(x: float) -> str:
    return f"{round(x * 100, 4):g}%"


def edge(metric, value) -> str:
    return f"{value:g}x" if metric.field in MULTIPLES else pct(value)


def band_row(metric) -> str:
    """The docs table row for a metric: every A/B/C/D edge plus the F condition."""
    good, bad = ("≥", "<") if metric.higher_is_better else ("≤", ">")
    cells = [f"{good} {edge(metric, e)}" for e in metric.bands]
    if metric.a_cap is not None:
        cells[0] = f"{edge(metric, metric.bands[0])} to {edge(metric, metric.a_cap)}"
        cells[1] += f" (or > {edge(metric, metric.a_cap)})"
    cells.append(f"{bad} {edge(metric, metric.bands[3])}")
    return f"| {metric.category} | `{metric.field}` | {metric.weight} | " + " | ".join(cells) + " |"


@pytest.mark.parametrize("metric", METRICS, ids=[m.field for m in METRICS])
def test_scorecard_row_matches_code(metric):
    assert band_row(metric) in SCORECARD


def test_scorecard_category_weights_and_points():
    for name, weight in CATEGORY_WEIGHTS.items():
        assert f"{name} {weight}" in SCORECARD
    for letter, points in GRADE_POINTS.items():
        assert f"| {letter} | {points:g} |" in SCORECARD
    for word in ("strong", "good", "mixed", "weak"):
        assert f"| {word} |" in SCORECARD


def test_scorecard_row_format_is_exercised():
    assert "| momentum | `technical.price_vs_sma200` | 5 | 0% to 20% | ≥ -5% (or > 20%) |" in SCORECARD
    assert "| valuation | `valuation.forward_pe` | 10 | ≤ 15x |" in SCORECARD


@pytest.mark.parametrize("rule", [f"L{i}" for i in range(1, 9)])
def test_labels_rule_ids(rule):
    assert f"| {rule} |" in LABELS


def test_labels_constants():
    assert f"coverage below {labels.MIN_COVERAGE:.0%}" in LABELS
    assert f"subscore below {labels.HEALTH_FAIL}" in LABELS
    assert f"score below {labels.SELL_SCORE} **and**" in LABELS
    assert f"| score below {labels.MIN_SCORE} |" in LABELS
    assert f"within {-labels.NEAR_HIGH:.0%} of the 52-week high" in LABELS
    assert f"at or above {labels.BIG_RUN:.0%}" in LABELS
    assert f"fair value × {1 + fair_value.BAND:g}" in LABELS


def test_fair_value_sector_defaults():
    for sector, pe in fair_value.SECTOR_DEFAULT_PE.items():
        assert f"| {sector} | {pe} |" in FAIR_VALUE
    assert f"| any other sector | {fair_value.DEFAULT_PE} |" in FAIR_VALUE


def test_fair_value_constants():
    assert f"(1 − {fair_value.BAND:.0%}) to fair value × (1 + {fair_value.BAND:.0%})" in FAIR_VALUE
    (top, top_mos), (mid, mid_mos) = fair_value.MOS_TIERS
    assert f"| ≥ {top} | {top_mos:.0%} |" in FAIR_VALUE
    assert f"| {mid}-{top - 0.1:g} | {mid_mos:.0%} |" in FAIR_VALUE
    assert f"| below {mid}, or no score | {fair_value.MOS_DEFAULT:.0%} |" in FAIR_VALUE
    assert f"below {fair_value.MIN_EARNINGS_YIELD:.0%}" in FAIR_VALUE
    assert f"most recent {fair_value.MAX_YEARS} at most" in FAIR_VALUE
    assert f"at least {fair_value.MIN_YEARS} such years" in FAIR_VALUE


def test_fair_value_limits_verbatim():
    limits = fair_value.__doc__.split("Stated limits (copied into every report):", 1)[1].strip()
    assert limits.count("\n- ") >= 6
    assert limits in FAIR_VALUE
