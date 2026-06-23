import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agents.judgment.judgment_agent import (
    _bottom_up_signals, _derive_alignment, _dominant_signal, JudgmentAgent,
)
from core.domain.models import (
    AnomalyReport, BottomUpResult, CreditBand, MarketRegime,
    PositionState, RiskAffinity, Signal,
)
from core.domain.taxonomy import Underlying, Wrapper


def _bu(underlying=Underlying.EQUITY, wrapper=Wrapper.SINGLE, **over):
    """Hilfsfunktion: minimaler BottomUpResult; underlying/wrapper direkt setzen."""
    base = dict(
        ticker="X", underlying=underlying, wrapper=wrapper,
        fundamentals=None, quality=None, short_interest=None, insider=None,
        earnings_trend=None, moat=None, valuation_range=None,
        precious_metals=None, bond=None, index=None, commodity_deep=None,
    )
    base.update(over)
    return BottomUpResult(**base)


def test_bond_overall_signal_drives_dominant_and_alignment():
    """Eine Anleihe trägt ihr Signal nur im BondResult.overall_signal — ohne Einspeisung
    bliebe die Empfehlung NEUTRAL (alle Equity-Bausteine sind None)."""
    bond = SimpleNamespace(overall_signal=Signal.BULLISH)
    bu = _bu(underlying=Underlying.BOND, bond=bond)
    sigs = _bottom_up_signals(bu)
    assert Signal.BULLISH in sigs
    assert _dominant_signal(sigs) == Signal.BULLISH
    assert _derive_alignment(sigs) == "aligned_bullish"


def test_equity_signals_unchanged_when_no_bond():
    """Equity-Pfad bleibt unverändert: die ersten sechs Positionen sind die Sub-Signale,
    der Anleihe-Slot ist None."""
    bu = _bu(fundamentals=SimpleNamespace(signal=Signal.BEARISH))
    sigs = _bottom_up_signals(bu)
    assert sigs[0] == Signal.BEARISH
    assert sigs[-1] is None
    assert _dominant_signal(sigs) == Signal.BEARISH


async def _to_thread_mock(fn, *args, **kw):
    return fn(*args, **kw)


def _run_and_capture_prompt(bottom_up):
    """Führt JudgmentAgent.run mit Fake-LLM aus und gibt den ersten (Urteils-)Prompt zurück."""
    llm = MagicMock()
    llm.complete.return_value = "Urteil"
    cockpit = MagicMock()
    cockpit.macro.regime = MarketRegime.EXPANSION
    cockpit.macro.regime_confidence = 0.70
    agent = JudgmentAgent(llm, MagicMock())
    with patch("asyncio.to_thread", side_effect=_to_thread_mock):
        asyncio.run(agent.run(
            ticker="TLT", top_down_context="Kontext", bottom_up=bottom_up,
            cockpit=cockpit, market="USA", current_position=PositionState.NONE,
            top_down_available=True, top_down_anomaly=AnomalyReport.empty(),
            bottom_up_anomaly=AnomalyReport.empty(), backtester_context={}))
    return llm.complete.call_args_list[0].args[0]


def test_bond_signal_appears_in_judgment_prompt():
    """Der LLM darf bei einer Anleihe nicht nur 'n/v' sehen — das aggregierte
    Gesamtsignal (inkl. Credit-Band/Affinität) muss im Prompt stehen, sonst
    widerspricht die XAI-Erklärung dem Alignment."""
    bond = SimpleNamespace(overall_signal=Signal.BULLISH,
                           credit_band=CreditBand.MITTEL,
                           risk_affinity=RiskAffinity.RISIKOFREUDIG)
    prompt = _run_and_capture_prompt(_bu(underlying=Underlying.BOND, bond=bond))
    assert "bullish" in prompt.lower()
    assert "mittel" in prompt.lower()
    assert "risikofreudig" in prompt.lower()
