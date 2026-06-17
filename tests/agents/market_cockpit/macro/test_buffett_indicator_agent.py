from agents.market_cockpit.macro.buffett_indicator_agent import _signal_from_z
from core.domain.models import Signal


def test_none_z_is_neutral():
    assert _signal_from_z(None) == Signal.NEUTRAL


def test_high_z_is_bearish():
    # +1.5σ über eigener Landeshistorie → historisch teuer → BEARISH
    assert _signal_from_z(1.6) == Signal.BEARISH


def test_low_z_is_bullish():
    assert _signal_from_z(-1.6) == Signal.BULLISH


def test_mid_z_is_neutral():
    assert _signal_from_z(0.5) == Signal.NEUTRAL


def test_swiss_high_ratio_with_normal_z_is_neutral():
    # CH bei 230% aber z≈0 (für CH normal) → NICHT BEARISH (kein 135%-Fix mehr)
    assert _signal_from_z(0.1) == Signal.NEUTRAL
