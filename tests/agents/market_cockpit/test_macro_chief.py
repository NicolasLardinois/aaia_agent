import asyncio
from unittest.mock import MagicMock, patch

from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from core.domain.models import Signal, LaborIncomeDataPoint, LaborIncomeSnapshot
from core.domain.regime import _score_indicator, INDICATOR_WEIGHTS


def test_yield_key_renamed():
    # alter irreführender Key weg, neuer da
    assert "yield_curve_3m_usa" not in INDICATOR_WEIGHTS
    assert "yield_curve_10y3m_usa" in INDICATOR_WEIGHTS


# ── Fix 2: labor-Signal in sub_signals (Task 19) ─────────────────────────────

def _default_mocks():
    macro = MagicMock()
    macro.get_extended_state.return_value = {}
    macro.get_economic_state.return_value = {}
    ecb = MagicMock()
    ecb.get_m2_growth.return_value = None
    ecb.get_m3_growth.return_value = None
    ecb.get_yield_spreads.return_value = {}
    snb = MagicMock()
    snb.get_m2_growth.return_value = None
    snb.get_m3_growth.return_value = None
    snb.get_yield_spreads.return_value = {}
    bus = MagicMock()
    return macro, ecb, snb, bus


def test_sub_signals_contains_labor():
    """sub_signals, das ans Regime weitergegeben wird, muss den 'labor'-Key enthalten (Task 19)."""
    macro, ecb, snb, bus = _default_mocks()
    agent = MacroChiefAgent(macro=macro, ecb=ecb, snb=snb, bus=bus)

    captured_sub_signals = {}

    original_detect = agent._detector.detect

    def capture_detect(state, sub_signals=None):
        if sub_signals is not None:
            captured_sub_signals.update(sub_signals)
        return original_detect(state, sub_signals=sub_signals)

    agent._detector.detect = capture_detect

    asyncio.run(agent.run())

    assert "labor" in captured_sub_signals, (
        f"'labor' fehlt in sub_signals; gefundene Keys: {list(captured_sub_signals.keys())}"
    )
