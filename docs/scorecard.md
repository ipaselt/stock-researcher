# Scorecard

## The lens

Long-term quality at a reasonable price, for a holder with a 1-5 year horizon. The scorecard asks four
questions in proportion to how much they matter over that horizon — is it cheap (valuation, 30), is it
growing (growth, 20), is it a good business (profitability, 20), can it survive a bad year (health, 20) — and
one timing question, weighted lightly (momentum, 10). All bands are absolute, not relative to the sector: a
forward P/E of 40 is expensive whatever the peers trade at. The code is `stock_researcher/scorecard.py`; the
`METRICS` table there is the single source of truth, and `tests/test_docs.py` fails if this page drifts from it.

## Grades and points

| Grade | Points |
|---|---|
| A | 10 |
| B | 7.5 |
| C | 5 |
| D | 2.5 |
| F | 0 |

**Boundary convention.** Each metric has four ordered thresholds, the A, B, C and D edges. For a
higher-is-better metric a value at or above the A edge is an A, at or above the B edge a B, and so on; below
the D edge is an F. For a lower-is-better metric the comparisons flip (at or below). A value exactly on a
threshold takes the **better** grade: a forward P/E of exactly 15 is an A, not a B.

Units: fractions are shown as percentages (0.06 = 6%), multiples with an `x` (15x). Stored values are always
fractions or multiples, never percents.

## The full table

| Category | Metric | Weight | A | B | C | D | F |
|---|---|---|---|---|---|---|---|
| valuation | `valuation.forward_pe` | 10 | ≤ 15x | ≤ 22x | ≤ 30x | ≤ 45x | > 45x |
| valuation | `valuation.peg` | 8 | ≤ 1x | ≤ 1.5x | ≤ 2.5x | ≤ 4x | > 4x |
| valuation | `valuation.ev_ebitda` | 6 | ≤ 10x | ≤ 15x | ≤ 22x | ≤ 30x | > 30x |
| valuation | `valuation.fcf_yield` | 6 | ≥ 6% | ≥ 4% | ≥ 2.5% | ≥ 1% | < 1% |
| growth | `growth.revenue_growth_yoy` | 6 | ≥ 20% | ≥ 12% | ≥ 6% | ≥ 0% | < 0% |
| growth | `growth.revenue_cagr_3y` | 6 | ≥ 15% | ≥ 10% | ≥ 5% | ≥ 0% | < 0% |
| growth | `growth.earnings_growth_yoy` | 4 | ≥ 20% | ≥ 10% | ≥ 3% | ≥ -10% | < -10% |
| growth | `growth.eps_cagr_3y` | 4 | ≥ 15% | ≥ 10% | ≥ 5% | ≥ 0% | < 0% |
| profitability | `profitability.gross_margin` | 4 | ≥ 55% | ≥ 40% | ≥ 30% | ≥ 20% | < 20% |
| profitability | `profitability.operating_margin` | 6 | ≥ 25% | ≥ 15% | ≥ 10% | ≥ 5% | < 5% |
| profitability | `profitability.roe` | 6 | ≥ 25% | ≥ 15% | ≥ 10% | ≥ 5% | < 5% |
| profitability | `profitability.fcf_margin` | 4 | ≥ 20% | ≥ 12% | ≥ 6% | ≥ 0% | < 0% |
| health | `health.debt_to_equity` | 6 | ≤ 0.3x | ≤ 0.7x | ≤ 1.2x | ≤ 2x | > 2x |
| health | `health.current_ratio` | 4 | ≥ 2x | ≥ 1.5x | ≥ 1x | ≥ 0.8x | < 0.8x |
| health | `health.interest_coverage` | 6 | ≥ 15x | ≥ 8x | ≥ 4x | ≥ 1.5x | < 1.5x |
| health | `health.cash_to_debt` | 4 | ≥ 1x | ≥ 0.5x | ≥ 0.25x | ≥ 0.1x | < 0.1x |
| momentum | `performance.rel_1y` | 5 | ≥ 15% | ≥ 5% | ≥ -5% | ≥ -15% | < -15% |
| momentum | `technical.price_vs_sma200` | 5 | 0% to 20% | ≥ -5% (or > 20%) | ≥ -15% | ≥ -25% | < -25% |

Category weights: valuation 30, growth 20, profitability 20, health 20, momentum 10 (total 100).

What the fields mean: `forward_pe` is price / next-year consensus EPS; `peg` is P/E divided by expected
growth; `ev_ebitda` is enterprise value / EBITDA; `fcf_yield` is trailing free cash flow / market cap;
`revenue_growth_yoy` and `earnings_growth_yoy` are the latest year-over-year rates; `revenue_cagr_3y` and
`eps_cagr_3y` are 3-year compound rates from the annual income statement (diluted EPS); `fcf_margin` is
trailing free cash flow / trailing revenue; `debt_to_equity` is total debt / shareholders' equity;
`interest_coverage` is EBIT / interest expense; `cash_to_debt` is cash / total debt; `rel_1y` is the 1-year
price return minus SPY's 1-year return (in percentage points); `price_vs_sma200` is price / 200-day simple
moving average − 1.

**The `price_vs_sma200` cap.** This one is not monotonic. The A band is the middle: 0% to +20% above the
200-day average (an uptrend that is not stretched). It is graded as a higher-is-better ladder (0% / -5% /
-15% / -25%) plus an A cap of +20%: a price more than 20% above its 200-day average is extended and grades B,
not A.

## Special cases (checked in this order)

1. `debt_to_equity` below 0 (negative shareholders' equity, typically from buybacks) → skipped, note
   "negative equity". The ratio has no meaningful reading, so it neither rewards nor punishes.
2. Total debt known and at or below 0 → `cash_to_debt` and `interest_coverage` grade A, note "no meaningful
   debt".
3. `interest_coverage` missing while debt is above 0 → skipped, note "no reported interest expense".
4. Any other missing value → skipped, note "missing".
5. `forward_pe`, `peg` or `ev_ebitda` at or below 0 → F, note "negative or zero" (negative earnings, growth
   or EBITDA).
6. `interest_coverage` below 0 (negative EBIT) → F, note "negative EBIT".

## Aggregation and coverage

- Each covered metric contributes `points / 10 × weight`.
- A category subscore is the sum of its covered metrics' contributions divided by their covered weight,
  × 100 (0-100).
- The total is the same sum over **all** covered metrics divided by the total covered weight, × 100, rounded
  to one decimal. Skipped metrics drop out and the remaining weights renormalize, so a missing field neither
  helps nor hurts the score.
- `coverage_pct` = covered weight / 100. Coverage below 60% means the score is not trusted: label rule L1
  (see `labels.md`) returns NOT LOOKING (data) regardless of the number.

## Band words

The band word is read off the rounded total, so the printed number is the number that decides.

| Total | Band word |
|---|---|
| ≥ 75 | strong |
| 60-74.9 | good |
| 45-59.9 | mixed |
| < 45 | weak |

## Why momentum is only 10%

For a holder with a 1-5 year horizon, price action is a timing input, not a quality input: a great business
that has sold off is usually a better purchase than the same business after a run, and a strong trend says
nothing about whether the company earns its cost of capital. Momentum is kept at all because it helps with
*when* to act (the HAS RUN label also looks at price action), but at full coverage it can move the total by
at most 10 points, so trend alone cannot carry a weak business into a good score.
