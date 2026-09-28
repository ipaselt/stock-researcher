# Fair value and entry price

One explainable, earnings-based method. The code is `stock_researcher/fair_value.py`; `tests/test_docs.py`
keeps this page in sync with its constants and its stated limits.

## The method, step by step

1. **Forward EPS.** Take consensus next-year EPS (`valuation.forward_eps`; when the provider omits it, price /
   forward P/E).
2. **Fair P/E.** For each of the last fiscal years in the annual income statement, compute the year-end P/E:
   the last close on or before the fiscal year-end divided by that year's diluted EPS. Keep only years with
   positive EPS, take the most recent 5 at most, and use their **median** — if at least 3 such years exist.
   The median rather than the mean, so one distorted year cannot move it far.
3. **Fallback.** With fewer than 3 usable years, use the sector default P/E from the table below (18 for a
   sector not in the table). The report records which source was used and how many years were usable.
4. **Fair value** = forward EPS × fair P/E.
5. **Band** = fair value × (1 − 15%) to fair value × (1 + 15%). A price above the high band is "above fair
   value" for the label rules.
6. **Margin of safety**, tiered by the scorecard total — a better business needs less cushion:

   | Scorecard total | Margin of safety |
   |---|---|
   | ≥ 75 | 5% |
   | 60-74.9 | 15% |
   | below 60, or no score | 20% |

7. **Entry price** = fair value × (1 − margin of safety). **Upside** = fair value / price − 1.

## Sector default P/E

| Sector | Default P/E |
|---|---|
| Technology | 25 |
| Communication Services | 18 |
| Healthcare | 20 |
| Consumer Defensive | 20 |
| Consumer Cyclical | 20 |
| Industrials | 19 |
| Financial Services | 13 |
| Energy | 12 |
| Utilities | 17 |
| Basic Materials | 14 |
| Real Estate | 20 |
| any other sector | 18 |

## When there is no fair value

- Forward EPS missing → no fair value, reason "forward EPS missing".
- Forward EPS at or below 0 → no fair value (a P/E on losses is meaningless).
- **Near-zero-EPS floor:** a forward earnings yield (forward EPS / price) below 1% — equivalently a forward
  P/E above 100 — → no fair value. Tiny positive earnings would otherwise produce a fair value that is pure
  noise. Exactly 1% is still computed; without a price the floor is skipped.

With no fair value there is no entry price, and (if no earlier rule fires) label rule L5 returns NOT LOOKING (the planner may override
it for a growth name, with a cited reason).

## Stated limits

These are printed in every report, read from the module docstring so the two cannot diverge.

- Banks and insurers are valued on book value (P/B), not earnings; this method is the wrong lens for them.
- REITs are valued on funds from operations (P/FFO); GAAP EPS understates them through depreciation.
- Cyclicals at peak earnings look cheap on a P/E exactly when they are most expensive.
- The historical median anchors to the past rate regime; a structurally different rate world shifts fair P/E.
- Consensus forward EPS can be stale or wrong; the fair value inherits that error one-for-one.
- Year-end P/E uses dividend-adjusted closes, which slightly understate older years' P/E.
- Pre-profit and near-zero-earnings companies (forward P/E > 100) get no fair value at all.
