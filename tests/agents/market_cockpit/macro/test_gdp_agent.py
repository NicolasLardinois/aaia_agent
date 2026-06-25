import asyncio
from unittest.mock import MagicMock

from agents.market_cockpit.macro.gdp_agent import (
    _signal, _sahm_recession, _sahm_from_history, GDPAgent,
)
from core.domain.models import Signal


def test_sahm_trigger_on_05pp_rise():
    # 3M-Schnitt 4.5% gegen 12M-Tief 3.9% = +0.6pp ≥ 0.5 → Rezessionssignal
    assert _sahm_recession(unemp_3m_avg=4.5, unemp_12m_low=3.9) is True


def test_sahm_no_trigger_below_05pp():
    assert _sahm_recession(unemp_3m_avg=4.2, unemp_12m_low=3.9) is False


def test_signal_normalizes_over_available_indicators():
    # Nur 2 Indikatoren vorhanden, beide positiv → BULLISH (Durchschnitt, nicht fixe Summe)
    assert _signal(gdp_above_trend=True, pmi=None, sahm=False) == Signal.BULLISH


def test_sahm_recession_forces_bearish():
    assert _signal(gdp_above_trend=True, pmi=55.0, sahm=True) == Signal.BEARISH


def test_all_none_is_neutral():
    assert _signal(gdp_above_trend=None, pmi=None, sahm=None) == Signal.NEUTRAL


# ── _sahm_from_history: Sahm-Regel aus monatlicher Arbeitslosen-Historie ───

def test_sahm_from_history_trigger():
    # 3M-Schnitt (4.3+4.5+4.6)/3 ≈ 4.47 gegen 12M-Tief 3.9 = +0.57pp ≥ 0.5 → True
    assert _sahm_from_history([3.9, 3.9, 4.0, 4.1, 4.3, 4.5, 4.6]) is True


def test_sahm_from_history_kein_trigger():
    # 3M-Schnitt ≈ 4.07 gegen 12M-Tief 3.9 = +0.17pp < 0.5 → False
    assert _sahm_from_history([3.9, 3.9, 3.9, 4.0, 4.0, 4.1, 4.1]) is False


def test_sahm_from_history_zu_kurz_none():
    # unter der Mindest-Historie (6 Monate) → kein verfrühter Rezessions-Call
    assert _sahm_from_history([4.5, 4.5, 4.5]) is None
    assert _sahm_from_history([]) is None


# ── run()-Wiring: EU-Arbeitslosen-Historie → Sahm → Signal ─────────────────

def _make_gdp_agent(*, ecb_gdp=None, ecb_unemp_hist=None, ecb_pmi=None):
    macro = MagicMock()
    macro.get_economic_state.return_value = {}
    ecb = MagicMock()
    ecb.get_gdp_growth.return_value = ecb_gdp
    ecb.get_unemployment.return_value = None
    ecb.get_unemployment_history.return_value = ecb_unemp_hist if ecb_unemp_hist is not None else []
    ecb.get_pmi.return_value = ecb_pmi
    snb = MagicMock()
    snb.get_gdp_growth.return_value = None
    snb.get_unemployment.return_value = None
    return GDPAgent(macro=macro, ecb=ecb, snb=snb, bus=MagicMock())


def test_eu_sahm_aus_history_erzwingt_bearish_via_run():
    """EU-BIP über Trend (sonst BULLISH), aber steigende Arbeitslosen-Historie →
    Sahm-Trigger dominiert → BEARISH."""
    agent = _make_gdp_agent(ecb_gdp=2.0, ecb_unemp_hist=[3.9, 3.9, 4.0, 4.1, 4.3, 4.5, 4.6])
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.BEARISH


def test_eu_ohne_history_unveraendert_via_run():
    """Leere History → Sahm None → BIP über Trend allein → BULLISH (verhaltens-erhaltend)."""
    agent = _make_gdp_agent(ecb_gdp=2.0)
    result = asyncio.run(agent.run())
    assert result.eurozone.signal == Signal.BULLISH
