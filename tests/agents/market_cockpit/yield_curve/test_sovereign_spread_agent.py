import asyncio
from unittest.mock import MagicMock, patch

from agents.market_cockpit.yield_curve.sovereign_spread_agent import _signal, _STRESS_COUNTRIES, _PERIPHERY
from core.domain.models import Signal


# ── Bug #29: Signal-Logik ──────────────────────────────────────────────────

def test_signal_neutral_when_all_spreads_below_200():
    spreads = {"IT_10y": 150.0, "ES_10y": 80.0, "FR_10y": 50.0}
    assert _signal(spreads) == Signal.NEUTRAL


def test_signal_bearish_when_max_spread_above_300():
    spreads = {"IT_10y": 420.0, "ES_10y": 180.0, "FR_10y": 90.0}
    assert _signal(spreads) == Signal.BEARISH


def test_signal_bearish_when_3_countries_above_200():
    spreads = {
        "IT_10y": 250.0, "ES_10y": 210.0, "PT_10y": 230.0,
        "FR_10y": 80.0,  "AT_10y": 30.0,
    }
    assert _signal(spreads) == Signal.BEARISH


def test_signal_neutral_when_only_2_countries_above_200():
    spreads = {"IT_10y": 210.0, "ES_10y": 205.0, "FR_10y": 60.0}
    assert _signal(spreads) == Signal.NEUTRAL


def test_signal_neutral_when_no_spreads():
    assert _signal({}) == Signal.NEUTRAL


# ── Bug #28: try/except statt isinstance ──────────────────────────────────

def test_sovereign_agent_returns_default_on_ecb_failure():
    from agents.market_cockpit.yield_curve.sovereign_spread_agent import SovereignSpreadAgent
    ecb = MagicMock()
    ecb.get_sovereign_yields.side_effect = Exception("ECB API down")
    bus = MagicMock()
    agent = SovereignSpreadAgent(ecb, bus)
    result = asyncio.run(agent.run())
    assert result.signal == Signal.NEUTRAL   # Default zurück, kein Crash


# ── Task 10: nur Peripherie in systemischer Zählung ──────────────────────

def test_core_countries_not_counted_in_systemic_rule():
    # 2 Peripherie >200 + 1 Kernland (NL) >200 → NICHT systemisch (nur Peripherie zählt)
    spreads = {"IT_10y": 210.0, "ES_10y": 220.0, "NL_10y": 205.0, "FR_10y": 60.0}
    assert _signal(spreads) == Signal.NEUTRAL


def test_three_periphery_above_200_is_bearish():
    spreads = {"IT_10y": 210.0, "ES_10y": 220.0, "PT_10y": 230.0, "NL_10y": 30.0}
    assert _signal(spreads) == Signal.BEARISH


def test_periphery_set_excludes_core():
    assert "IT" in _PERIPHERY and "NL" not in _PERIPHERY and "FI" not in _PERIPHERY


# ── Alle Eurozone-Länder vorhanden ────────────────────────────────────────

def test_all_eurozone_countries_in_spreads_by_country():
    from agents.market_cockpit.yield_curve.sovereign_spread_agent import EUROZONE_COUNTRIES
    assert "IT" in EUROZONE_COUNTRIES
    assert "MT" in EUROZONE_COUNTRIES
    assert "HR" in EUROZONE_COUNTRIES
    assert len(EUROZONE_COUNTRIES) == 20   # alle 20 Eurozone-Mitglieder
