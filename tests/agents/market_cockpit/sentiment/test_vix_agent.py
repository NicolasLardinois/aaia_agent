from agents.market_cockpit.sentiment.vix_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(None, None) == Signal.NEUTRAL


def test_vix_spike_is_bullish_contrarian():
    # VIX > 30 = Panik = contrarian Kaufsignal → BULLISH (konsistent mit Sentiment-Block)
    assert _signal(35.0, None) == Signal.BULLISH


def test_low_vix_is_bearish_complacency():
    # VIX < 15 = Sorglosigkeit → BEARISH
    assert _signal(12.0, None) == Signal.BEARISH


def test_mid_vix_is_neutral():
    assert _signal(20.0, None) == Signal.NEUTRAL


def test_vix_zero_does_not_fall_back_to_vstoxx():
    # vix=0.0 ist gültig (kein Falsiness-Fallback auf vstoxx)
    assert _signal(0.0, 40.0) == Signal.BEARISH   # 0.0 < 15 → BEARISH, NICHT vstoxx
