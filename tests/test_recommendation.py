from core.domain.recommendation import derive_recommendation
from core.domain.models import PositionState, Signal, Recommendation
from core.domain.taxonomy import Underlying, Wrapper


def _base(market: str) -> dict:
    return dict(
        alignment="aligned_bearish",
        signal=Signal.BEARISH,
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        current_position=PositionState.NONE,
        market=market,
        cockpit=None,
        top_down_available=True,
        confidence=0.75,
    )


def test_bearish_no_position_returns_none():
    result = derive_recommendation(**_base("USA"))
    assert result.action == Recommendation.NONE


def test_bearish_long_position_sells():
    result = derive_recommendation(
        alignment="aligned_bearish",
        signal=Signal.BEARISH,
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        current_position=PositionState.LONG,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.75,
    )
    assert result.action == Recommendation.SELL


def test_bullish_no_position_buys():
    result = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        current_position=PositionState.NONE,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.75,
    )
    assert result.action == Recommendation.BUY


def test_short_position_defers_long_lens():
    result = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        current_position=PositionState.SHORT,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.75,
    )
    assert result.action == Recommendation.NONE


def test_lowercase_market_bearish_no_position_returns_none():
    result = derive_recommendation(**_base("de"))
    assert result.action == Recommendation.NONE
