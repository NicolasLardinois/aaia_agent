from core.domain.recommendation import derive_recommendation
from core.domain.models import AnomalyReport, Signal, Recommendation


def _short_report():
    return AnomalyReport(signals=[], contradictions=[], severity="none")


def _base(market: str) -> dict:
    return dict(
        alignment="aligned_bearish",
        signal=Signal.BEARISH,
        asset_class="equity",
        in_portfolio=False,
        market=market,
        cockpit=None,
        top_down_available=True,
        confidence=0.75,
    )


def test_uppercase_market_gets_short():
    result = derive_recommendation(**_base("USA"))
    assert result.action == Recommendation.SHORT


def test_lowercase_market_gets_short():
    result = derive_recommendation(**_base("usa"))
    assert result.action == Recommendation.SHORT


def test_mixed_case_market_gets_short():
    result = derive_recommendation(**_base("Usa"))
    assert result.action == Recommendation.SHORT


def test_market_with_whitespace_gets_short():
    result = derive_recommendation(**_base(" USA "))
    assert result.action == Recommendation.SHORT


def test_lowercase_eurozone_market_gets_short():
    result = derive_recommendation(**_base("de"))
    assert result.action == Recommendation.SHORT
