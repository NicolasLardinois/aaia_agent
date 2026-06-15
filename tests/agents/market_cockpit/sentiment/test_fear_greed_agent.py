from agents.market_cockpit.sentiment.fear_greed_agent import _label, _signal
from core.domain.models import Signal


def test_value_55_label_matches_signal():
    assert _label(55) == "Neutral"
    assert _signal(55) == Signal.NEUTRAL, f"Expected NEUTRAL, got {_signal(55)}"


def test_value_75_is_bearish():
    assert _signal(75) == Signal.BEARISH


def test_value_45_is_bullish():
    assert _signal(45) == Signal.BULLISH


def test_value_25_is_bullish():
    assert _signal(25) == Signal.BULLISH


def test_value_76_is_bearish():
    assert _signal(76) == Signal.BEARISH


def test_value_74_is_neutral():
    assert _signal(74) == Signal.NEUTRAL
