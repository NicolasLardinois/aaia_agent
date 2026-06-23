import pytest

from core.domain.recommendation import derive_recommendation, _position_size_pct
from core.domain.models import PositionState, Signal, Recommendation
from core.domain.taxonomy import Underlying, Wrapper


def test_size_unchanged_without_leverage():
    assert _position_size_pct(1.0) == 10.0
    assert _position_size_pct(1.0, leverage=None) == 10.0


def test_size_scaled_down_by_leverage():
    # 10× Hebel → Kapitaleinsatz = Nominal/10; Tranche entsprechend kleiner.
    assert _position_size_pct(1.0, leverage=10.0) == pytest.approx(1.0)


def test_size_never_negative_or_above_cap():
    assert _position_size_pct(0.50, leverage=10.0) >= 0.0
    assert _position_size_pct(1.0, leverage=1.0) <= 10.0


def test_size_floored_for_high_leverage_buy():
    # Sehr hoher Hebel (niedrige Margin) darf die empfohlene Tranche nicht auf 0.0 %
    # runden — wer einen Kauf empfiehlt, nennt eine sichtbare Größe (kein "BUY ~0.0%").
    assert _position_size_pct(0.50, leverage=80.0) >= 0.1


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


def test_buy_reasoning_marks_leverage_as_capital_not_notional():
    # Mit Future-Hebel ist die genannte Größe der Kapitaleinsatz, nicht das Markt-Exposure
    # → der Text muss das Nominal-Exposure ausweisen, sonst untertreibt er das Risiko.
    result = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        underlying=Underlying.COMMODITY,
        wrapper=Wrapper.FUTURE,
        current_position=PositionState.NONE,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.90,
        leverage=10.0,
    )
    assert result.action == Recommendation.BUY
    assert "Kapitaleinsatz" in result.reasoning
    assert "Nominal" in result.reasoning


def test_buy_plus_reasoning_marks_leverage_as_capital_not_notional():
    result = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        underlying=Underlying.COMMODITY,
        wrapper=Wrapper.FUTURE,
        current_position=PositionState.LONG,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.90,
        leverage=10.0,
    )
    assert result.action == Recommendation.BUY_PLUS
    assert "Kapitaleinsatz" in result.reasoning
    assert "Nominal" in result.reasoning


def test_buy_reasoning_unchanged_without_leverage():
    # Ohne Hebel bleibt der bisherige Text (Regressions-Schutz für den Nicht-Future-Pfad).
    result = derive_recommendation(
        alignment="aligned_bullish",
        signal=Signal.BULLISH,
        underlying=Underlying.EQUITY,
        wrapper=Wrapper.SINGLE,
        current_position=PositionState.NONE,
        market="USA",
        cockpit=None,
        top_down_available=True,
        confidence=0.90,
    )
    assert "des Risikobudgets" in result.reasoning
    assert "Kapitaleinsatz" not in result.reasoning


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
