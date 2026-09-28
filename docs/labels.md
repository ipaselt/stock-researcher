# Labels

The scorecard, fair value and snapshot produce a **suggested label** by fixed rules; the planner then
confirms or overrides it. The code is `stock_researcher/labels.py`; `tests/test_docs.py` keeps this page in
sync with its constants.

## The rules (first match wins)

The rule id that fired is written into the report and the ledger. "Fair-value high band" means
fair value × 1.15 (the ±15% band from `fair-value.md`).

| Rule | Condition | Label |
|---|---|---|
| L1 | coverage below 60%, or no score at all | NOT LOOKING (data) |
| L2 | health category subscore below 30 | NOT LOOKING (balance sheet) |
| L3 | score below 45 **and** price above the fair-value high band | SELL |
| L4 | score below 55 | NOT LOOKING |
| L5 | no fair value (EPS missing, ≤ 0, or forward P/E > 100) | NOT LOOKING (the planner may override for growth names) |
| L6 | price at or below the entry price | BUY |
| L7 | price above the fair-value high band **and** (within 5% of the 52-week high **or** 1-year return at or above 40%) | HAS RUN |
| L8 | otherwise | WAIT, with the entry target |

Details that decide edge cases:

- "Below" is strict: a score of exactly 45 is not below 45, a coverage of exactly 60% passes L1.
- "Within 5% of the 52-week high" means `pct_from_52w_high` ≥ −5%.
- A health subscore of None (nothing in the category covered) does not trigger L2.
- An unavailable price fails every price test (L3, L6, L7) and falls through to L8 (WAIT with the entry
  target).
- L6, L7 and L8 carry the entry target (fair value × (1 − margin of safety)); L1-L5 carry none.

## What each label means for the owner's process

- **BUY** — the price is at or below the entry price: a good-enough business (score ≥ 55) trading at a margin
  of safety below fair value. Start or add to a position, sized by conviction.
- **WAIT** — a good-enough business priced above the entry price (or with no price) that has not been
  flagged HAS RUN. Keep it on the watchlist with the entry target as a price alert.
- **HAS RUN** — the price is above fair value's high band and the stock is near its 52-week high or up 40%+
  in a year. Do not chase; if held, it is a candidate to trim; revisit after a pullback.
- **SELL** — a weak business (score below 45) priced above fair value. If held, exit; if not, avoid.
- **NOT LOOKING** — not a candidate right now: too little data (L1), a failing balance sheet (L2), a
  mediocre score (L4), or no earnings-based fair value (L5). Do nothing and do not re-run soon unless
  something changes.

## Override protocol

The rules are deliberately mechanical; the planner's judgment sits on top of them, visibly:

1. An override names the **rule id** that fired, the **new label**, and **one reason** that cites a number
   from the snapshot or score file (with its key, e.g. `valuation.forward_pe`) or a specific agent finding.
2. The planner writes it into `data/<T>/verdict.md` front-matter: `label_final` and `override_reason`
   (`none` when the suggested label is confirmed). `assemble` refuses a verdict whose `label_final` differs
   from the suggestion while `override_reason` is `none`.
3. **Both labels are kept.** The report front-matter and `reports/ratings.csv` carry `label_suggested`,
   `rule_id` and `label_final`, so every override is auditable and the rules' hit rate can be measured
   against the planner's later.
