from agents.market_cockpit.macro.money_supply_agent import _signal
from core.domain.models import Signal


def test_none_is_neutral():
    assert _signal(excess_liquidity=None, velocity_trend=None) == Signal.NEUTRAL


def test_moderate_excess_is_bullish():
    # 0–4% Überschuss-Liquidität = gesunde Expansion → BULLISH
    assert _signal(excess_liquidity=2.0, velocity_trend=None) == Signal.BULLISH


def test_excessive_liquidity_is_bearish():
    # >5% Überschuss = Inflations-/Blasenrisiko → BEARISH
    assert _signal(excess_liquidity=6.0, velocity_trend=None) == Signal.BEARISH


def test_contraction_is_bearish():
    # M wächst langsamer als BIP (negativ) = Liquiditätsentzug → BEARISH
    assert _signal(excess_liquidity=-3.0, velocity_trend=None) == Signal.BEARISH


def test_gap_region_no_longer_neutral():
    # vormalige 8–10%-Lücke: hier z.B. 4.5% Überschuss → eindeutig (BEARISH-Flanke)
    assert _signal(excess_liquidity=4.5, velocity_trend=None) == Signal.BEARISH


def test_excess_dampened_by_falling_velocity():
    # 6% Überschuss aber stark fallende Velocity → Inflationswirkung gedämpft → NEUTRAL
    assert _signal(excess_liquidity=6.0, velocity_trend="falling") == Signal.NEUTRAL
