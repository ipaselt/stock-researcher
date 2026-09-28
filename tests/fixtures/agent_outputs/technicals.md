## Technicals — AAPL
### Findings
- Trend regime is firmly up: price 340.15 (meta.price) sits above both the 50-day average 321.9 (technical.sma_50) and the 200-day average 287.7 (technical.sma_200), with a golden cross in place (technical.golden_cross = true).
- The stock is stretched above its long-term trend: 18.7% above the 200-day (technical.price_vs_sma200) and 6.1% above the 50-day (technical.price_vs_sma50).
- It is trading at the top of its range: -1.1% from the 52-week high of 345.34 (technical.pct_from_52w_high, technical.week52_high) and 40.4% above the 52-week low of 243.42 (technical.pct_from_52w_low, technical.week52_low). RSI(14) is 66.2 (technical.rsi_14): firm, but below the conventional 70 overbought line.
- Relative strength vs the S&P 500 is strong on both horizons: 1-year return 34.2% (performance.return_1y) vs SPY 17.5% (performance.spy_return_1y), rel_1y 16.7% (performance.rel_1y); 3-year return 102.0% (performance.return_3y) vs SPY 85.7% (performance.spy_return_3y), rel_3y 16.7% (performance.rel_3y).
- Drawdown over the past year was contained: max 1-year drawdown -13.8% (performance.max_drawdown_1y), with beta 1.085 (meta.beta).
- The scorecard's momentum category scores 100.0 (categories.momentum.score), both inputs graded A (performance.rel_1y, technical.price_vs_sma200).

### Assessment
The tape is unambiguously healthy: a golden cross, price above both moving averages, and outperformance of the S&P 500 by 16.7% over one year (performance.rel_1y) and 16.7% over three (performance.rel_3y). That is a trend a holder wants to own, not fight. The timing read is different: at -1.1% from the 52-week high (technical.pct_from_52w_high) and 18.7% above the 200-day average (technical.price_vs_sma200), the stock is extended, and the last year's -13.8% drawdown (performance.max_drawdown_1y) shows the size of pullback that has occurred inside this trend. RSI of 66.2 (technical.rsi_14) is not yet overbought, so this is extension rather than a blow-off. For a 1-5 year holder, momentum supports the name but the entry window is poor; staged buying or waiting for a reversion toward the 50-day 321.9 (technical.sma_50) or 200-day 287.7 (technical.sma_200) is the better timing posture.

### Risks and caveats
- Extension cuts both ways: 18.7% above the 200-day (technical.price_vs_sma200) leaves room for a mean-reversion pullback without the trend breaking.
- The snapshot holds no volume, breadth or multi-timeframe data, so the quality of the breakout near the 52-week high cannot be judged.
- Relative strength is measured only against SPY; there is no sector or peer benchmark in the snapshot.
- Max drawdown is only available for 1 year (performance.max_drawdown_1y); there are no 3- or 5-year drawdown fields to judge tail risk over the holding horizon.
- This is a single-date snapshot (meta.as_of 2026-09-28); there is no series to confirm whether RSI is rising or rolling over.
- There are no nulls in the technical or performance sections.

### Grade: B · Confidence: medium
```json
{"dimension": "technicals", "grade": "B", "confidence": "medium",
 "numbers_cited": [
  {"key": "meta.price", "value": 340.15},
  {"key": "meta.beta", "value": 1.085},
  {"key": "technical.sma_50", "value": 321.87675415039064},
  {"key": "technical.sma_200", "value": 287.70651588439944},
  {"key": "technical.golden_cross", "value": true},
  {"key": "technical.price_vs_sma200", "value": 0.18748125778863578},
  {"key": "technical.price_vs_sma50", "value": 0.061347721171859604},
  {"key": "technical.pct_from_52w_high", "value": -0.01067064342387214},
  {"key": "technical.week52_high", "value": 345.34},
  {"key": "technical.pct_from_52w_low", "value": 0.4035617451318707},
  {"key": "technical.week52_low", "value": 243.42},
  {"key": "technical.rsi_14", "value": 66.17095833057978},
  {"key": "performance.return_1y", "value": 0.3423316244028314},
  {"key": "performance.spy_return_1y", "value": 0.1748955374375285},
  {"key": "performance.rel_1y", "value": 0.16743608696530288},
  {"key": "performance.return_3y", "value": 1.0197467405728085},
  {"key": "performance.spy_return_3y", "value": 0.8567963133052516},
  {"key": "performance.rel_3y", "value": 0.16721081480599054},
  {"key": "performance.max_drawdown_1y", "value": -0.13798523953754416},
  {"key": "categories.momentum.score", "value": 100.0}
 ],
 "flags": ["extended"],
 "suggested_label_adjustment": null,
 "reason": "Strong uptrend (golden cross) with rel_1y 16.7% (performance.rel_1y), but price is -1.1% from the 52-week high (technical.pct_from_52w_high), which supports the scorecard's HAS RUN timing call rather than moving it."}
```
