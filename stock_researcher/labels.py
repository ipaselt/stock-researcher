"""Suggested label: the first matching rule of L1-L8 wins; the rule id and the numbers it used are recorded.

L1 coverage < 60% (or no score)                     -> NOT LOOKING (data)
L2 health category score < 30                        -> NOT LOOKING (balance sheet)
L3 score < 45 and price > fair-value high band       -> SELL
L4 score < 55                                        -> NOT LOOKING
L5 no fair value                                     -> NOT LOOKING (the planner may override for growth names)
L6 price <= entry price                              -> BUY
L7 price > fair-value high band and (within 5% of the 52-week high or 1y return >= 40%) -> HAS RUN
L8 otherwise                                         -> WAIT, with the entry target
The fair-value high band is fair_value x 1.15 (fair_value.BAND). A price that is unavailable fails every
price test and falls through to L8.
"""
from dataclasses import dataclass

MIN_COVERAGE = 0.60
HEALTH_FAIL = 30
SELL_SCORE = 45
MIN_SCORE = 55
NEAR_HIGH = -0.05  # pct_from_52w_high at or above this = within 5% of the high
BIG_RUN = 0.40  # 1y return at or above this


@dataclass
class LabelSuggestion:
    label: str
    rule_id: str
    reason: str
    entry_target: float | None = None


def suggest_label(score, fv, snapshot) -> LabelSuggestion:
    total, price = score.total, snapshot.meta.price
    health = score.categories["health"].score

    if total is None or score.coverage_pct < MIN_COVERAGE:
        return LabelSuggestion("NOT LOOKING", "L1", f"insufficient data (coverage {score.coverage_pct:.0%})")
    if health is not None and health < HEALTH_FAIL:
        return LabelSuggestion("NOT LOOKING", "L2", f"balance-sheet fail (health score {health:.1f} < {HEALTH_FAIL})")
    above_band = price is not None and fv.band_high is not None and price > fv.band_high
    if total < SELL_SCORE and above_band:
        return LabelSuggestion(
            "SELL", "L3", f"score {total:.1f} < {SELL_SCORE} and price {price:.2f} > fair-value high {fv.band_high:.2f}"
        )
    if total < MIN_SCORE:
        return LabelSuggestion("NOT LOOKING", "L4", f"score {total:.1f} < {MIN_SCORE}")
    if fv.fair_value is None:
        return LabelSuggestion(
            "NOT LOOKING", "L5", f"no fair value ({fv.reason}); planner may override for growth names"
        )
    entry = fv.entry_price
    if price is not None and price <= entry:
        return LabelSuggestion("BUY", "L6", f"price {price:.2f} <= entry {entry:.2f}", entry)
    if above_band:
        from_high, ret_1y = snapshot.technical.pct_from_52w_high, snapshot.performance.return_1y
        if from_high is not None and from_high >= NEAR_HIGH:
            why = f"{from_high:.1%} from 52w high"
        elif ret_1y is not None and ret_1y >= BIG_RUN:
            why = f"1y return {ret_1y:.1%}"
        else:
            why = None
        if why:
            return LabelSuggestion(
                "HAS RUN", "L7", f"price {price:.2f} > fair-value high {fv.band_high:.2f} and {why}", entry
            )
    if price is None:
        return LabelSuggestion("WAIT", "L8", f"price unavailable; entry {entry:.2f}", entry)
    return LabelSuggestion("WAIT", "L8", f"price {price:.2f} > entry {entry:.2f} (fair value {fv.fair_value:.2f})", entry)
