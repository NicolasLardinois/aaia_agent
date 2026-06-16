import asyncio
from unittest.mock import MagicMock

import pytest

from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent, _signal
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


# ── Fix 1: None-Guard ─────────────────────────────────────────────────────────

def _make_agent(*, eu_m3=None, eu_m2=None, ch_m3=None, ch_m2=None, ext=None):
    """Hilfs-Factory: erstellt MoneySupplyAgent mit gemockten Providern."""
    macro = MagicMock()
    macro.get_extended_state.return_value = ext or {}
    ecb = MagicMock()
    ecb.get_m2_growth.return_value = eu_m2
    ecb.get_m3_growth.return_value = eu_m3
    snb = MagicMock()
    snb.get_m2_growth.return_value = ch_m2
    snb.get_m3_growth.return_value = ch_m3
    bus = MagicMock()
    return MoneySupplyAgent(macro=macro, ecb=ecb, snb=snb, bus=bus)


def test_eu_money_supply_no_gdp_no_crash():
    """EU-Geldmenge vorhanden, nominales BIP None → kein TypeError, Signal NEUTRAL."""
    agent = _make_agent(eu_m3=5.0)  # eu_m gesetzt, aber eu_nom_gdp bleibt None
    result = asyncio.run(agent.run())
    # Kein Crash; Signal muss NEUTRAL sein (excess kann nicht berechnet werden)
    assert result.eurozone.signal == Signal.NEUTRAL


def test_ch_money_supply_no_gdp_no_crash():
    """CH-Geldmenge vorhanden, nominales BIP None → kein TypeError, Signal NEUTRAL."""
    agent = _make_agent(ch_m3=4.0)  # ch_m gesetzt, aber ch_nom_gdp bleibt None
    result = asyncio.run(agent.run())
    assert result.switzerland.signal == Signal.NEUTRAL
