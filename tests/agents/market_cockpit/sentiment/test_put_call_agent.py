from agents.market_cockpit.sentiment.put_call_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(None) == Signal.NEUTRAL


def test_high_z_is_bullish_contrarian():
    # P/C deutlich über rollierendem Mittel (z > +1) = Pessimismus → BULLISH
    assert _signal(1.2) == Signal.BULLISH


def test_low_z_is_bearish_contrarian():
    # P/C deutlich unter Mittel (z < -1) = Sorglosigkeit → BEARISH
    assert _signal(-1.2) == Signal.BEARISH


def test_mid_z_is_neutral():
    assert _signal(0.3) == Signal.NEUTRAL
