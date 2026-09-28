import pytest

from stock_researcher.normalize import FIELDS, UNITS, news_items, normalize


def test_every_field_has_a_valid_unit_and_target():
    for key, target, unit in FIELDS:
        assert unit in UNITS, key
        group, field = target.split(".")
        assert group and field


def test_dividend_yield_is_a_percent():
    groups, _ = normalize({"dividendYield": 0.32})
    assert groups["dividend"]["dividend_yield"] == pytest.approx(0.0032)


def test_debt_to_equity_is_a_percent():
    groups, _ = normalize({"debtToEquity": 78.4})
    assert groups["health"]["debt_to_equity"] == pytest.approx(0.784)


def test_fraction_passes_through():
    groups, _ = normalize({"grossMargins": 0.46})
    assert groups["profitability"]["gross_margin"] == 0.46


def test_missing_and_none_keys_are_tracked():
    groups, missing = normalize({"grossMargins": 0.46, "beta": None})
    assert "beta" in missing and "trailingPE" in missing
    assert "grossMargins" not in missing
    assert set(missing) == {key for key, _, _ in FIELDS} - {"grossMargins"}


def test_fallback_key_fills_the_same_field():
    groups, missing = normalize({"regularMarketPrice": 10.0, "trailingPegRatio": 1.5})
    assert groups["meta"]["price"] == 10.0
    assert groups["valuation"]["peg"] == 1.5
    assert "currentPrice" in missing and "pegRatio" in missing


def test_primary_key_wins_over_fallback():
    groups, _ = normalize({"currentPrice": 11.0, "regularMarketPrice": 10.0})
    assert groups["meta"]["price"] == 11.0


def test_unusable_numbers_become_missing_with_a_warning():
    groups, missing = normalize({"trailingPE": "Infinity", "forwardPE": float("nan")})
    assert "trailingPE" in missing and "forwardPE" in missing
    assert "trailing_pe" not in groups.get("valuation", {})
    assert any("trailingPE" in w for w in groups["meta"]["warnings"])


def test_no_warnings_for_sane_values():
    groups, _ = normalize({"dividendYield": 0.32, "debtToEquity": 78.4, "grossMargins": 0.46, "forwardPE": 30.0})
    assert groups["meta"]["warnings"] == []


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
    groups, _ = normalize(info)
    assert any(needle in w for w in groups["meta"]["warnings"])


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
    ]
    items = news_items(raw)
    assert items == [
        {"title": "A", "summary": "s", "url": "https://x/a", "provider": "P", "published": "2026-01-01T00:00:00Z"},
        {"title": "B", "summary": "", "url": None, "provider": None, "published": None},
    ]
    assert len(news_items(raw, limit=1)) == 1
