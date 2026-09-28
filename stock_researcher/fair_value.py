"""Earnings-based fair value and entry price: one explainable method.

fair_value = forward_eps x fair_pe, where fair_pe is the median year-end P/E over the last 3-5 fiscal years
(positive-EPS years only; needs >= 3 of them), else the per-sector default in SECTOR_DEFAULT_PE (18 for an
unknown sector). The source is recorded. Band: fair_value x (1 -/+ BAND). Margin of safety is tiered by the
scorecard total: >= 75 -> 5%, 60-74 -> 15%, < 60 or no score -> 20%; entry_price = fair_value x (1 - mos).
Forward EPS missing or <= 0 -> no fair value, with the reason. Near-zero earnings: a forward earnings
yield (forward_eps / price) below MIN_EARNINGS_YIELD (1%, i.e. forward P/E > 100) -> no fair value either;
exactly 1% is still computed. Without a price this floor is skipped.

Stated limits (copied into every report):
- Banks and insurers are valued on book value (P/B), not earnings; this method is the wrong lens for them.
- REITs are valued on funds from operations (P/FFO); GAAP EPS understates them through depreciation.
- Cyclicals at peak earnings look cheap on a P/E exactly when they are most expensive.
- The historical median anchors to the past rate regime; a structurally different rate world shifts fair P/E.
- Consensus forward EPS can be stale or wrong; the fair value inherits that error one-for-one.
- Year-end P/E uses dividend-adjusted closes, which slightly understate older years' P/E.
- Pre-profit and near-zero-earnings companies (forward P/E > 100) get no fair value at all.
"""
import math
import statistics
from dataclasses import dataclass

from .snapshot import safe_div

SECTOR_DEFAULT_PE = {
    "Technology": 25,
    "Communication Services": 18,
    "Healthcare": 20,
    "Consumer Defensive": 20,
    "Consumer Cyclical": 20,
    "Industrials": 19,
    "Financial Services": 13,
    "Energy": 12,
    "Utilities": 17,
    "Basic Materials": 14,
    "Real Estate": 20,
}
DEFAULT_PE = 18
MIN_YEARS, MAX_YEARS = 3, 5
BAND = 0.15
MOS_TIERS = ((75, 0.05), (60, 0.15))  # (min score, margin of safety), best first
MOS_DEFAULT = 0.20
MIN_EARNINGS_YIELD = 0.01  # forward_eps / price below this (forward P/E > 100) -> no earnings-based fair value


@dataclass
class FairValue:
    forward_eps: float | None
    fair_pe: float
    fair_pe_source: str  # "historical_median" | "sector_default"
    n_years: int
    fair_value: float | None
    band_low: float | None
    band_high: float | None
    margin_of_safety: float
    entry_price: float | None
    upside: float | None
    reason: str | None  # None when computed, else why not


def median_pe(pes: list[float] | None) -> tuple[float | None, int]:
    """(median of the last MAX_YEARS usable P/Es, n usable); the median only when n >= MIN_YEARS."""
    usable = [p for p in (pes or []) if p is not None and math.isfinite(p) and p > 0][:MAX_YEARS]
    n = len(usable)
    return (statistics.median(usable) if n >= MIN_YEARS else None), n


def margin_of_safety(score_total: float | None) -> float:
    if score_total is not None:
        for min_score, mos in MOS_TIERS:
            if score_total >= min_score:
                return mos
    return MOS_DEFAULT


def compute_fair_value(snapshot, score_total: float | None) -> FairValue:
    eps = snapshot.valuation.forward_eps
    median, n = median_pe(snapshot.valuation.fiscal_year_pe)
    if median is not None:
        fair_pe, source = median, "historical_median"
    else:
        fair_pe, source = SECTOR_DEFAULT_PE.get(snapshot.meta.sector, DEFAULT_PE), "sector_default"
    mos = margin_of_safety(score_total)
    price = snapshot.meta.price
    if price is not None and price <= 0:
        price = None
    reason = None
    if eps is None or not math.isfinite(eps):
        reason = "forward EPS missing"
    elif eps <= 0:
        reason = f"forward EPS {eps:.2f} <= 0"
    elif price is not None and eps / price < MIN_EARNINGS_YIELD:
        reason = (f"forward earnings yield {eps / price:.2%} below 1% (forward P/E > 100): "
                  "earnings-based fair value not meaningful")
    if reason:
        return FairValue(eps, fair_pe, source, n, None, None, None, mos, None, None, reason)
    fv = eps * fair_pe
    upside = None if price is None else safe_div(fv, price) - 1
    return FairValue(eps, fair_pe, source, n, fv, fv * (1 - BAND), fv * (1 + BAND), mos, fv * (1 - mos), upside, None)
