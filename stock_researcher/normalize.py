"""yfinance → Snapshot translation: the ONLY place yfinance keys appear outside the provider.

Every stored ratio is a fraction or a multiple, never a percent. Each info key carries an explicit unit code:
  raw  — pass through (multiples, prices, counts)
  frac — already a fraction (0.46 = 46%)
  pct  — a percent; divided by 100 (yfinance's dividendYield 0.32 means 0.32%)
  usd  — a dollar amount
  str  — text
Several keys may target the same field: the first non-missing one wins (e.g. currentPrice, then
regularMarketPrice). Every info key that is None/absent/unusable is reported in fields_missing.
"""
import math

UNITS = {"raw", "frac", "pct", "usd", "str"}

FIELDS: list[tuple[str, str, str]] = [
    # meta
    ("longName", "meta.name", "str"),
    ("shortName", "meta.name", "str"),
    ("sector", "meta.sector", "str"),
    ("industry", "meta.industry", "str"),
    ("exchange", "meta.exchange", "str"),
    ("currency", "meta.currency", "str"),
    ("currentPrice", "meta.price", "raw"),
    ("regularMarketPrice", "meta.price", "raw"),
    ("marketCap", "meta.market_cap", "usd"),
    ("beta", "meta.beta", "raw"),
    # valuation
    ("trailingPE", "valuation.trailing_pe", "raw"),
    ("forwardPE", "valuation.forward_pe", "raw"),
    ("pegRatio", "valuation.peg", "raw"),
    ("trailingPegRatio", "valuation.peg", "raw"),
    ("enterpriseToEbitda", "valuation.ev_ebitda", "raw"),
    ("priceToSalesTrailing12Months", "valuation.price_to_sales", "raw"),
    ("priceToBook", "valuation.price_to_book", "raw"),
    ("forwardEps", "valuation.forward_eps", "raw"),
    ("trailingEps", "valuation.trailing_eps", "raw"),
    # growth
    ("revenueGrowth", "growth.revenue_growth_yoy", "frac"),
    ("earningsGrowth", "growth.earnings_growth_yoy", "frac"),
    ("earningsQuarterlyGrowth", "growth.earnings_quarterly_growth", "frac"),
    # profitability
    ("grossMargins", "profitability.gross_margin", "frac"),
    ("operatingMargins", "profitability.operating_margin", "frac"),
    ("profitMargins", "profitability.net_margin", "frac"),
    ("returnOnEquity", "profitability.roe", "frac"),
    ("returnOnAssets", "profitability.roa", "frac"),
    # health
    ("debtToEquity", "health.debt_to_equity", "pct"),
    ("currentRatio", "health.current_ratio", "raw"),
    ("totalCash", "health.total_cash", "usd"),
    ("totalDebt", "health.total_debt", "usd"),
    ("freeCashflow", "health.free_cashflow", "usd"),
    ("operatingCashflow", "health.operating_cashflow", "usd"),
    # performance
    ("52WeekChange", "performance.week52_change", "frac"),
    ("SandP52WeekChange", "performance.sp500_week52_change", "frac"),
    # dividend
    ("dividendYield", "dividend.dividend_yield", "pct"),
    ("payoutRatio", "dividend.payout_ratio", "frac"),
    # analyst
    ("recommendationMean", "analyst.recommendation_mean", "raw"),
    ("recommendationKey", "analyst.recommendation_key", "str"),
    ("numberOfAnalystOpinions", "analyst.num_analysts", "raw"),
    ("targetMeanPrice", "analyst.target_mean", "raw"),
    ("targetMedianPrice", "analyst.target_median", "raw"),
    ("targetHighPrice", "analyst.target_high", "raw"),
    ("targetLowPrice", "analyst.target_low", "raw"),
    # technical (sma_50/sma_200 are recomputed from history when it is long enough)
    ("fiftyTwoWeekHigh", "technical.week52_high", "raw"),
    ("fiftyTwoWeekLow", "technical.week52_low", "raw"),
    ("fiftyDayAverage", "technical.sma_50", "raw"),
    ("twoHundredDayAverage", "technical.sma_200", "raw"),
    # ownership
    ("heldPercentInsiders", "ownership.insiders_pct", "frac"),
    ("heldPercentInstitutions", "ownership.institutions_pct", "frac"),
]

# Annual income-statement row labels used for derived fields.
INCOME_ROWS = {
    "revenue": "Total Revenue",
    "eps": "Diluted EPS",
    "net_income": "Net Income",
    "ebit": "EBIT",
    "interest_expense": "Interest Expense",
}


def _number(value) -> float | None:
    """A finite float, or None (bools, strings like 'Infinity', NaN and inf are unusable)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def normalize(info: dict) -> tuple[dict, list[str]]:
    """Map a raw info dict to {group: {field: value}} plus the info keys that were missing.

    Sanity warnings are returned under the "warnings" key of the "meta" group; they never raise.
    """
    out: dict[str, dict] = {}
    missing: list[str] = []
    warnings: list[str] = []
    for key, target, unit in FIELDS:
        raw = info.get(key)
        if unit == "str":
            value = str(raw) if raw not in (None, "") else None
        else:
            value = _number(raw)
            if value is None and raw is not None:
                warnings.append(f"{key}: unusable value {raw!r} treated as missing")
            if value is not None and unit == "pct":
                value = value / 100
            if value is not None and unit == "frac" and abs(value) > 5:
                warnings.append(f"{key} = {value} looks like a percent, not a fraction")
        if value is None:
            missing.append(key)
            continue
        group, field = target.split(".")
        out.setdefault(group, {}).setdefault(field, value)

    dividend_yield = out.get("dividend", {}).get("dividend_yield")
    if dividend_yield is not None and dividend_yield > 0.25:
        warnings.append(f"dividend_yield = {dividend_yield} is above 25% — check units")
    debt_to_equity = out.get("health", {}).get("debt_to_equity")
    if debt_to_equity is not None and debt_to_equity > 50:
        warnings.append(f"debt_to_equity = {debt_to_equity} is above 50x — check units")
    forward_pe = out.get("valuation", {}).get("forward_pe")
    if forward_pe is not None and forward_pe < 0:
        warnings.append("forward_pe < 0: negative forward earnings")
    out.setdefault("meta", {})["warnings"] = warnings
    return out, missing


def news_items(raw_items: list, limit: int = 10) -> list[dict]:
    """Flatten yfinance news items (nested under 'content'); malformed items are skipped."""
    items = []
    for raw in raw_items:
        content = raw.get("content") if isinstance(raw, dict) else None
        if not isinstance(content, dict) or not content.get("title"):
            continue
        url = (content.get("canonicalUrl") or {}).get("url") or (content.get("clickThroughUrl") or {}).get("url")
        items.append(
            {
                "title": content["title"],
                "summary": content.get("summary") or "",
                "url": url,
                "provider": (content.get("provider") or {}).get("displayName"),
                "published": content.get("pubDate"),
            }
        )
        if len(items) == limit:
            break
    return items
