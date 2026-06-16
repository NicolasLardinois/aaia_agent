from agents.market_cockpit.macro.gdp_agent import _signal, _sahm_recession
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
