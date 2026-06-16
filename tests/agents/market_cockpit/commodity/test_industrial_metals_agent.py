from agents.market_cockpit.commodity.industrial_metals_agent import _signal
from core.domain.models import Signal


def test_no_momentum_is_neutral():
    assert _signal(copper_gold_z=0.0) == Signal.NEUTRAL


def test_rising_copper_gold_ratio_is_bullish():
    # Dr. Copper steigt relativ zu Gold → Risk-on / Wachstum → BULLISH
    assert _signal(copper_gold_z=1.3) == Signal.BULLISH


def test_falling_copper_gold_ratio_is_bearish():
    # Kupfer fällt relativ zu Gold → Flucht in Sicherheit → BEARISH
    assert _signal(copper_gold_z=-1.3) == Signal.BEARISH


def test_none_is_neutral():
    assert _signal(copper_gold_z=None) == Signal.NEUTRAL
