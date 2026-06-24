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

def _make_agent(*, eu_m3=None, eu_m2=None, eu_gdp=None, eu_cpi=None,
                ch_m3=None, ch_m2=None, ext=None):
    """Hilfs-Factory: erstellt MoneySupplyAgent mit gemockten Providern.

    eu_gdp/eu_cpi muessen explizit gesetzt werden, sonst liefert der MagicMock
    fuer ecb.get_gdp_growth/get_cpi ein Truthy-Objekt statt None.
    """
    macro = MagicMock()
    macro.get_extended_state.return_value = ext or {}
    ecb = MagicMock()
    ecb.get_m2_growth.return_value = eu_m2
    ecb.get_m3_growth.return_value = eu_m3
    ecb.get_gdp_growth.return_value = eu_gdp
    ecb.get_cpi.return_value = eu_cpi
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


def test_usa_money_supply_no_nominal_gdp_no_crash():
    """USA-Geldmenge vorhanden, aber nominales BIP None (gdp_growth fehlt) →
    kein TypeError, USA-Signal NEUTRAL."""
    # usa_m2 ist gesetzt, inflation ist gesetzt, aber gdp_growth fehlt →
    # usa_nom_gdp bleibt None → excess_over_nominal_gdp(5.0, None) würde TypeError werfen
    agent = _make_agent(ext={"m2_growth": 5.0, "inflation": 3.0})
    result = asyncio.run(agent.run())
    assert result.usa.signal == Signal.NEUTRAL


def test_eu_signal_schaltet_scharf_mit_echten_inputs():
    """M3=2.7, reales BIP=0.3, CPI=2.0 → nom BIP=2.3 → excess=0.4 → BULLISH."""
    agent = _make_agent(eu_m3=2.7, eu_gdp=0.3, eu_cpi=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.BULLISH


def test_eu_faellt_auf_m2_zurueck_wenn_m3_fehlt():
    """M3 fehlt, M2=2.9 + BIP/CPI → eu_m nutzt M2 → excess 0.6 → BULLISH."""
    agent = _make_agent(eu_m2=2.9, eu_gdp=0.3, eu_cpi=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.m2_growth == 2.9
    assert result.eurozone.signal == Signal.BULLISH


def test_eu_neutral_wenn_cpi_fehlt():
    """M3 + BIP vorhanden, CPI fehlt → eu_nom_gdp None → NEUTRAL (kein Crash)."""
    agent = _make_agent(eu_m3=2.7, eu_gdp=0.3, eu_cpi=None)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.NEUTRAL


def test_eu_neutral_wenn_bip_fehlt():
    """M3 + CPI vorhanden, reales BIP fehlt → eu_nom_gdp None → NEUTRAL (symmetrisch zum CPI-Fall)."""
    agent = _make_agent(eu_m3=2.7, eu_gdp=None, eu_cpi=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.NEUTRAL
