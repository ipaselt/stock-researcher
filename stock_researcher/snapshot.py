"""The Snapshot: one ticker's normalized data, grouped so agents can be pointed at sections by name.

Every numeric field is a float or None; ratios are fractions or multiples, never percents.
"""
import dataclasses
import datetime as dt
import json
import math
from dataclasses import dataclass, field

import pandas as pd

from . import technicals
from .normalize import INCOME_ROWS, news_items, normalize


@dataclass
class Meta:
    ticker: str = ""
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    exchange: str | None = None
    currency: str | None = None
    as_of: str | None = None
    provider: str | None = None
    price: float | None = None
    market_cap: float | None = None
    beta: float | None = None
    warnings: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)


@dataclass
class Valuation:
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg: float | None = None
    ev_ebitda: float | None = None
    price_to_sales: float | None = None
    price_to_book: float | None = None
    forward_eps: float | None = None
    trailing_eps: float | None = None
    fcf_yield: float | None = None
    earnings_yield: float | None = None
    fiscal_year_pe: list[float] | None = None  # year-end P/E per fiscal year, positive-EPS years, most recent first


@dataclass
class Growth:
    revenue_growth_yoy: float | None = None
    earnings_growth_yoy: float | None = None
    earnings_quarterly_growth: float | None = None
    revenue_cagr_3y: float | None = None
    eps_cagr_3y: float | None = None
    net_income_cagr_3y: float | None = None


@dataclass
class Profitability:
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roa: float | None = None
    revenue_ttm: float | None = None
    fcf_margin: float | None = None


@dataclass
class Health:
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    net_debt: float | None = None
    free_cashflow: float | None = None
    operating_cashflow: float | None = None
    interest_coverage: float | None = None
    cash_to_debt: float | None = None


@dataclass
class Performance:
    return_ytd: float | None = None
    return_1y: float | None = None
    return_3y: float | None = None
    return_5y: float | None = None
    spy_return_ytd: float | None = None
    spy_return_1y: float | None = None
    spy_return_3y: float | None = None
    spy_return_5y: float | None = None
    rel_1y: float | None = None
    rel_3y: float | None = None
    max_drawdown_1y: float | None = None
    week52_change: float | None = None
    sp500_week52_change: float | None = None


@dataclass
class Dividend:
    dividend_yield: float | None = None
    payout_ratio: float | None = None


@dataclass
class Analyst:
    recommendation_mean: float | None = None
    recommendation_key: str | None = None
    target_mean: float | None = None
    target_median: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    num_analysts: float | None = None
    upside_to_target_mean: float | None = None


@dataclass
class Technical:
    week52_high: float | None = None
    week52_low: float | None = None
    pct_from_52w_high: float | None = None
    pct_from_52w_low: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    price_vs_sma50: float | None = None
    price_vs_sma200: float | None = None
    rsi_14: float | None = None
    golden_cross: bool | None = None


@dataclass
class Ownership:
    insiders_pct: float | None = None
    institutions_pct: float | None = None


@dataclass
class Events:
    next_earnings_date: str | None = None
    news: list[dict] = field(default_factory=list)


@dataclass
class Snapshot:
    meta: Meta = field(default_factory=Meta)
    valuation: Valuation = field(default_factory=Valuation)
    growth: Growth = field(default_factory=Growth)
    profitability: Profitability = field(default_factory=Profitability)
    health: Health = field(default_factory=Health)
    performance: Performance = field(default_factory=Performance)
    dividend: Dividend = field(default_factory=Dividend)
    analyst: Analyst = field(default_factory=Analyst)
    technical: Technical = field(default_factory=Technical)
    ownership: Ownership = field(default_factory=Ownership)
    events: Events = field(default_factory=Events)


GROUPS = {f.name: f.default_factory for f in dataclasses.fields(Snapshot)}


def _num(x) -> float | None:
    """A finite float, or None."""
    if x is None or isinstance(x, bool):
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def safe_div(a, b) -> float | None:
    """a / b, or None when either is missing or b is zero."""
    a, b = _num(a), _num(b)
    if a is None or b is None or b == 0:
        return None
    return _num(a / b)


def _sub(a, b) -> float | None:
    return None if a is None or b is None else a - b


def _income_value(income: pd.DataFrame, row: str, col: int = 0) -> float | None:
    if row not in income.index or col >= len(income.columns):
        return None
    return _num(income.loc[row].iloc[col])


def _income_cagr(income: pd.DataFrame, row: str, years: int) -> float | None:
    """CAGR from the annual column `years` fiscal years before the latest one (None if that column is absent)."""
    if row not in income.index or income.columns.empty:
        return None
    dates = pd.to_datetime(income.columns)
    for i, date in enumerate(dates):
        span = (dates[0] - date).days / 365.25
        if round(span) == years:
            return technicals.cagr(_income_value(income, row, i), _income_value(income, row, 0), span)
    return None


def _closes(history: pd.DataFrame) -> pd.Series:
    if history is None or history.empty or "Close" not in history:
        return pd.Series(dtype=float)
    close = history["Close"].dropna()
    if getattr(close.index, "tz", None) is not None:
        close.index = close.index.tz_localize(None)
    return close


def _last(series: pd.Series) -> float | None:
    series = series.dropna()
    return _num(series.iloc[-1]) if not series.empty else None


def fiscal_year_pe(close: pd.Series, income: pd.DataFrame) -> list[float]:
    """Year-end P/E per annual income-statement column, most recent first.

    P/E = last close on/before the fiscal year-end ÷ that year's Diluted EPS. Years with missing or
    non-positive EPS, or no close on/before the date, are skipped.
    """
    row = INCOME_ROWS["eps"]
    if close.empty or row not in income.index or income.columns.empty:
        return []
    eps = pd.Series(income.loc[row].to_numpy(), index=pd.to_datetime(income.columns))
    out = []
    for date in sorted(eps.index, reverse=True):
        e = _num(eps[date])
        prior = close[close.index <= date]
        if e is None or e <= 0 or prior.empty:
            continue
        pe = safe_div(prior.iloc[-1], e)
        if pe is not None:
            out.append(pe)
    return out


def fields_missing(snapshot: Snapshot) -> list[str]:
    """`group.field` paths of every numeric field that is None."""
    missing = []
    for group in dataclasses.fields(snapshot):
        section = getattr(snapshot, group.name)
        for f in dataclasses.fields(section):
            if f.type == float | None and getattr(section, f.name) is None:
                missing.append(f"{group.name}.{f.name}")
    return missing


def build_snapshot(provider, ticker: str, as_of: str | None = None) -> Snapshot:
    """Fetch everything for `ticker` (plus SPY history) and assemble a Snapshot."""
    info = provider.fetch_info(ticker)
    close = _closes(provider.fetch_history(ticker, period="5y"))
    spy_close = _closes(provider.fetch_history("SPY", period="5y"))
    income = provider.fetch_income_stmt(ticker)
    if income is None:
        income = pd.DataFrame()
    raw_news = provider.fetch_news(ticker, limit=10) or []
    targets = provider.fetch_analyst_targets(ticker) or {}
    earnings_dates = provider.fetch_earnings_dates(ticker) or []
    as_of = as_of or dt.date.today().isoformat()

    groups, warnings = normalize(info)
    meta = groups.setdefault("meta", {})
    val = groups.setdefault("valuation", {})
    gro = groups.setdefault("growth", {})
    prof = groups.setdefault("profitability", {})
    hea = groups.setdefault("health", {})
    perf = groups.setdefault("performance", {})
    ana = groups.setdefault("analyst", {})
    tech = groups.setdefault("technical", {})

    meta.update(ticker=ticker, as_of=as_of, provider=getattr(provider, "name", None), warnings=warnings)
    if close.empty:
        warnings.append("no price history")
    price = meta.get("price")

    # valuation
    if val.get("forward_eps") is None:
        val["forward_eps"] = safe_div(price, val.get("forward_pe"))
    val["fcf_yield"] = safe_div(hea.get("free_cashflow"), meta.get("market_cap"))
    val["earnings_yield"] = safe_div(1, val.get("trailing_pe"))
    val["fiscal_year_pe"] = fiscal_year_pe(close, income) or None

    # growth (annual income statement)
    gro["revenue_cagr_3y"] = _income_cagr(income, INCOME_ROWS["revenue"], 3)
    gro["eps_cagr_3y"] = _income_cagr(income, INCOME_ROWS["eps"], 3)
    gro["net_income_cagr_3y"] = _income_cagr(income, INCOME_ROWS["net_income"], 3)

    # profitability / health
    # freeCashflow is trailing-twelve-month: divide by TTM revenue; the last fiscal year is only a fallback.
    revenue = prof.get("revenue_ttm")
    if revenue is None:
        revenue = _income_value(income, INCOME_ROWS["revenue"])
    prof["fcf_margin"] = safe_div(hea.get("free_cashflow"), revenue)
    interest = _income_value(income, INCOME_ROWS["interest_expense"])
    ebit = _income_value(income, INCOME_ROWS["ebit"])
    hea["interest_coverage"] = safe_div(ebit, None if interest is None else abs(interest))
    hea["net_debt"] = _sub(hea.get("total_debt"), hea.get("total_cash"))
    hea["cash_to_debt"] = safe_div(hea.get("total_cash"), hea.get("total_debt"))

    # performance
    mine, spy = technicals.period_returns(close), technicals.period_returns(spy_close)
    for period in ("ytd", "1y", "3y", "5y"):
        perf[f"return_{period}"] = mine[period]
        perf[f"spy_return_{period}"] = spy[period]
    perf["rel_1y"] = _sub(mine["1y"], spy["1y"])
    perf["rel_3y"] = _sub(mine["3y"], spy["3y"])
    perf["max_drawdown_1y"] = technicals.max_drawdown(close)

    # analyst: info targets first, the provider's price targets as fallback
    for fld, key in (("target_mean", "mean"), ("target_median", "median"), ("target_high", "high"), ("target_low", "low")):
        if ana.get(fld) is None:
            ana[fld] = _num(targets.get(key))
    ana["upside_to_target_mean"] = _sub(safe_div(ana.get("target_mean"), price), 1)

    # technical: SMAs computed from history when long enough; the info averages are the fallback
    for window in (50, 200):
        if len(close) >= window:
            tech[f"sma_{window}"] = _last(technicals.sma(close, window))
    from_high = _sub(safe_div(price, tech.get("week52_high")), 1)
    from_low = _sub(safe_div(price, tech.get("week52_low")), 1)
    tech["pct_from_52w_high"] = None if from_high is None else min(from_high, 0.0)
    tech["pct_from_52w_low"] = None if from_low is None else max(from_low, 0.0)
    tech["price_vs_sma50"] = _sub(safe_div(price, tech.get("sma_50")), 1)
    tech["price_vs_sma200"] = _sub(safe_div(price, tech.get("sma_200")), 1)
    tech["rsi_14"] = _last(technicals.rsi(close)) if not close.empty else None
    sma50, sma200 = tech.get("sma_50"), tech.get("sma_200")
    tech["golden_cross"] = None if sma50 is None or sma200 is None else sma50 > sma200

    upcoming = sorted(d for d in earnings_dates if d >= as_of)
    groups["events"] = {"next_earnings_date": upcoming[0] if upcoming else None, "news": news_items(raw_news, 10)}

    snapshot = Snapshot(**{name: cls(**groups.get(name, {})) for name, cls in GROUPS.items()})
    snapshot.meta.fields_missing = fields_missing(snapshot)
    return snapshot


def to_json(snapshot: Snapshot) -> str:
    return json.dumps(dataclasses.asdict(snapshot), indent=2, allow_nan=False)


def from_json(text: str) -> Snapshot:
    data = json.loads(text)
    return Snapshot(**{name: cls(**data.get(name, {})) for name, cls in GROUPS.items()})
