import pytest

from stock_researcher.normalize import FIELDS, UNITS, news_items, normalize


def test_every_field_has_a_valid_unit_and_target():
    for key, target, unit in FIELDS:
        assert unit in UNITS, key
        group, field = target.split(".")
        assert group and field


def test_only_dividend_yield_and_debt_to_equity_are_percents():
    assert {key for key, _, unit in FIELDS if unit == "pct"} == {"dividendYield", "debtToEquity"}


@pytest.mark.parametrize("key, target", [(k, t) for k, t, u in FIELDS if u in ("frac", "raw")])
def test_frac_and_raw_pass_through(key, target):
    groups, warnings = normalize({key: 0.46})
    group, field = target.split(".")
    assert groups[group][field] == 0.46
    assert warnings == []


def test_dividend_yield_is_a_percent():
    groups, _ = normalize({"dividendYield": 0.32})
    assert groups["dividend"]["dividend_yield"] == pytest.approx(0.0032)


def test_debt_to_equity_is_a_percent():
    groups, _ = normalize({"debtToEquity": 78.4})
    assert groups["health"]["debt_to_equity"] == pytest.approx(0.784)


def test_fraction_passes_through():
    groups, _ = normalize({"grossMargins": 0.46})
    assert groups["profitability"]["gross_margin"] == 0.46


def test_none_and_absent_keys_are_left_out():
    groups, _ = normalize({"grossMargins": 0.46, "beta": None})
    assert groups == {"profitability": {"gross_margin": 0.46}}


def test_fallback_key_fills_the_same_field():
    groups, _ = normalize({"regularMarketPrice": 10.0, "trailingPegRatio": 1.5})
    assert groups["meta"]["price"] == 10.0
    assert groups["valuation"]["peg"] == 1.5


def test_primary_key_wins_over_fallback():
    groups, _ = normalize({"currentPrice": 11.0, "regularMarketPrice": 10.0})
    assert groups["meta"]["price"] == 11.0


def test_unusable_numbers_become_missing_with_a_warning():
    groups, warnings = normalize({"trailingPE": "Infinity", "forwardPE": float("nan")})
    assert "valuation" not in groups
    assert any("trailingPE" in w for w in warnings)


def test_no_warnings_for_sane_values():
    _, warnings = normalize({"dividendYield": 0.32, "debtToEquity": 78.4, "grossMargins": 0.46, "forwardPE": 30.0})
    assert warnings == []


@pytest.mark.parametrize(
    "info, needle",
    [
        ({"dividendYield": 30.0}, "dividend_yield"),  # 30% after /100 — a unit flip upstream
        ({"debtToEquity": 5100.0}, "debt_to_equity"),
        ({"grossMargins": 46.0}, "grossMargins"),
        ({"revenueGrowth": -6.0}, "revenueGrowth"),
        ({"forwardPE": -8.6}, "negative forward earnings"),
    ],
)
def test_sanity_warnings(info, needle):
    _, warnings = normalize(info)
    assert any(needle in w for w in warnings)


def test_strings_pass_through():
    groups, _ = normalize({"longName": "Apple Inc.", "recommendationKey": "buy"})
    assert groups["meta"]["name"] == "Apple Inc."
    assert groups["analyst"]["recommendation_key"] == "buy"


def test_news_items_flatten_and_skip_malformed():
    raw = [
        {"content": {"title": "A", "summary": "s", "pubDate": "2026-01-01T00:00:00Z",
                     "canonicalUrl": {"url": "https://x/a"}, "provider": {"displayName": "P"}}},
        {"content": None},
        "junk",
        {"content": {"summary": "no title"}},
        {"content": {"title": "B"}},
        {"content": {"title": "x", "canonicalUrl": "https://a"}},
        {"content": {"title": "y", "provider": "P"}},
    ]
    items = news_items(raw)
    assert items == [
        {"title": "A", "summary": "s", "url": "https://x/a", "provider": "P", "published": "2026-01-01T00:00:00Z"},
        {"title": "B", "summary": "", "url": None, "provider": None, "published": None},
    ]
    assert len(news_items(raw, limit=1)) == 1
