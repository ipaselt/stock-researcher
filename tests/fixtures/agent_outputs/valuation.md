## Valuation — AAPL
### Findings
- The price of 340.15 (meta.price) sits above our earnings-based fair value of 295.06 (fair_value.fair_value) and just above the top of the fair-value band of 339.32 (fair_value.band_high). The implied upside is -13.6% (fair_value.upside), and the margin-of-safety entry price is 250.80 (fair_value.entry_price).
- The fair value applies a fair P/E of 30.8x (fair_value.fair_pe), the historical median over 4 fiscal years (fair_value.n_years), to forward EPS of 9.59 (fair_value.forward_eps). The stock trades at a forward P/E of 35.5x (valuation.forward_pe) and a trailing P/E of 39.0x (valuation.trailing_pe), both above its own median.
- Fiscal-year P/Es in the lookback range from 22.2x to 38.0x (valuation.fiscal_year_pe), so the 30.8x median already includes a period of elevated multiples. The current forward multiple is near the top of that range.
- Other multiples are rich too: PEG 2.74 (valuation.peg), EV/EBITDA 29.8x (valuation.ev_ebitda), price/sales 10.6x (valuation.price_to_sales), FCF yield 2.2% (valuation.fcf_yield) and earnings yield 2.6% (valuation.earnings_yield). All four scored metrics grade D, and the valuation category scores 25.0 (categories.valuation.score).
- Growth does not support the multiple over a full cycle. 3-year EPS CAGR is 6.9% (growth.eps_cagr_3y) and 3-year revenue CAGR is 1.8% (growth.revenue_cagr_3y), against a latest year of 28.7% earnings growth (growth.earnings_growth_yoy) and 16.4% revenue growth (growth.revenue_growth_yoy). Profitability is elite: 32.6% operating margin (profitability.operating_margin) and 23.1% FCF margin (profitability.fcf_margin).
- The consensus mean target of 328.22 (analyst.target_mean) is below the price, giving -3.9% upside (analyst.upside_to_target_mean). The median target is 340.0 (analyst.target_median), and targets span 215.0 to 405.0 (analyst.target_low, analyst.target_high) across 39 analysts (analyst.num_analysts), with a "buy" consensus (analyst.recommendation_key, mean 2.2 on analyst.recommendation_mean). The 0.3% dividend yield (dividend.dividend_yield) at a 12.0% payout ratio (dividend.payout_ratio) adds almost no valuation support.

### Assessment
An earnings multiple is a fair lens for AAPL. It is a consistently profitable, cash-generative company, and a 12.0% payout (dividend.payout_ratio) means returns come mostly through buybacks rather than dividends. On that lens the stock is fully priced to overpriced: the forward multiple of 35.5x (valuation.forward_pe) is above its own 30.8x median (fair_value.fair_pe), and a PEG of 2.74 (valuation.peg) leans on a single strong year rather than the 6.9% 3-year EPS trend (growth.eps_cagr_3y). The analyst mean target of 328.22 (analyst.target_mean) and our fair value of 295.06 (fair_value.fair_value) both sit below the price. Ours is more conservative and anchored to history, so it is the more credible floor. For a 1-5 year holder, returns from here depend on sustained double-digit EPS growth, not multiple expansion.

### Risks and caveats
- The fair P/E comes from only 4 fiscal years (fair_value.n_years), and that window includes multiples as high as 38.0x (valuation.fiscal_year_pe). A longer history might set a lower median, so the fair value may be generous rather than harsh.
- If the latest year's 28.7% earnings growth (growth.earnings_growth_yoy) reflects a product cycle rather than a new trend, the forward EPS of 9.59 (valuation.forward_eps) may be close to peak-cycle. That would overstate fair value. The 3-year EPS CAGR of 6.9% (growth.eps_cagr_3y) is the more conservative anchor.
- Price/book of 46.2x (valuation.price_to_book) and ROE of 148.8% (profitability.roe) are distorted by heavy buybacks shrinking equity. Book-based lenses are not meaningful here.
- No valuation fields are null. The only missing snapshot field is health.interest_coverage (meta.fields_missing), which is outside this dimension.
- Analyst targets are widely dispersed, from 215.0 to 405.0 (analyst.target_low, analyst.target_high), so the consensus is a weak anchor.

### Grade: D · Confidence: medium
```json
{"dimension": "valuation", "grade": "D", "confidence": "medium",
 "numbers_cited": [
  {"key": "meta.price", "value": 340.15},
  {"key": "fair_value.fair_value", "value": 295.0573284748453},
  {"key": "fair_value.band_high", "value": 339.3159277460721},
  {"key": "fair_value.upside", "value": -0.136388047906427},
  {"key": "fair_value.entry_price", "value": 250.79872920361848},
  {"key": "fair_value.fair_pe", "value": 30.782113170081978},
  {"key": "fair_value.n_years", "value": 4},
  {"key": "fair_value.forward_eps", "value": 9.58535},
  {"key": "valuation.forward_eps", "value": 9.58535},
  {"key": "valuation.forward_pe", "value": 35.486446},
  {"key": "valuation.trailing_pe", "value": 38.963345},
  {"key": "valuation.fiscal_year_pe", "value": [34.00708727798257, 38.0044560683401, 27.557139062181385, 22.18520294039612]},
  {"key": "valuation.peg", "value": 2.74},
  {"key": "valuation.ev_ebitda", "value": 29.767},
  {"key": "valuation.price_to_sales", "value": 10.634031},
  {"key": "valuation.price_to_book", "value": 46.21603},
  {"key": "valuation.fcf_yield", "value": 0.021699699621797797},
  {"key": "valuation.earnings_yield", "value": 0.0256651475893561},
  {"key": "categories.valuation.score", "value": 25.0},
  {"key": "growth.eps_cagr_3y", "value": 0.06879057105281716},
  {"key": "growth.revenue_cagr_3y", "value": 0.01812118576492483},
  {"key": "growth.earnings_growth_yoy", "value": 0.287},
  {"key": "growth.revenue_growth_yoy", "value": 0.164},
  {"key": "profitability.operating_margin", "value": 0.32623002},
  {"key": "profitability.fcf_margin", "value": 0.23075529328407707},
  {"key": "profitability.roe", "value": 1.4875101},
  {"key": "analyst.target_mean", "value": 328.22205},
  {"key": "analyst.upside_to_target_mean", "value": -0.03931729376125026},
  {"key": "analyst.target_median", "value": 340.0},
  {"key": "analyst.target_low", "value": 215.0},
  {"key": "analyst.target_high", "value": 405.0},
  {"key": "analyst.num_analysts", "value": 39.0},
  {"key": "analyst.recommendation_mean", "value": 2.20455},
  {"key": "dividend.dividend_yield", "value": 0.0032},
  {"key": "dividend.payout_ratio", "value": 0.1204}
 ],
 "flags": ["method_fit:ok"], "suggested_label_adjustment": null,
 "reason": "Price 340.15 (meta.price) sits at the top of the fair-value band 339.32 (fair_value.band_high) with a forward P/E of 35.5x (valuation.forward_pe) above the 30.8x historical median (fair_value.fair_pe), consistent with the scorecard's HAS RUN label, so no adjustment."}
```
