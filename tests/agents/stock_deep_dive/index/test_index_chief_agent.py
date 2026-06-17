from agents.stock_deep_dive.index_chief_agent import _aggregate_index_signal
from core.domain.models import Signal


def test_bewertung_und_momentum_bullish_ist_bullish():
    sig, conf = _aggregate_index_signal(
        valuation_sig=Signal.BULLISH,
        momentum_sig=Signal.BULLISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.BULLISH
    assert conf > 0.0


def test_bewertung_bullish_momentum_bearish_konflikt():
    """Gegenläufige gleich gewichtete Hauptsignale → NEUTRAL (Konfliktauflösung)."""
    sig, _ = _aggregate_index_signal(
        valuation_sig=Signal.BULLISH,
        momentum_sig=Signal.BEARISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL


def test_alle_neutral_ist_neutral():
    sig, conf = _aggregate_index_signal(
        valuation_sig=Signal.NEUTRAL, momentum_sig=Signal.NEUTRAL,
        earnings_sig=Signal.NEUTRAL, breadth_sig=Signal.NEUTRAL,
        price_sig=Signal.NEUTRAL,
    )
    assert sig == Signal.NEUTRAL
    assert conf == 0.0


def test_momentum_und_breadth_bearish_ist_bearish():
    sig, _ = _aggregate_index_signal(
        valuation_sig=Signal.NEUTRAL,
        momentum_sig=Signal.BEARISH,
        earnings_sig=Signal.NEUTRAL,
        breadth_sig=Signal.BEARISH,
        price_sig=Signal.BEARISH,
    )
    assert sig == Signal.BEARISH
