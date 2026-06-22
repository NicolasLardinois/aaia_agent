import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

from orchestrators.judgment_orchestrator import JudgmentOrchestrator
from core.domain.models import (
    DeepDiveResult, InvestmentRecommendation, Recommendation, AnomalyReport,
    ConflictResolution, PositionState,
)


def _result(conflict):
    rec = InvestmentRecommendation(action=Recommendation.HOLD, short_type=None,
                                   short_warning=None, confidence=0.6, reasoning="x")
    return DeepDiveResult(
        ticker="X", asset_class="equity", market="USA", top_down_context="",
        top_down_available=True, judgment="", alignment="mixed", recommendation=rec,
        conflict=conflict, conflict_reason=("Konflikt" if conflict else ""))


def _orch(result):
    o = JudgmentOrchestrator.__new__(JudgmentOrchestrator)
    o.memory = MagicMock()
    o.memory.load_history.return_value = []
    o.memory.load_global_history.return_value = []
    o.anomaly_chief = MagicMock()
    o.anomaly_chief.run.return_value = (AnomalyReport.empty(), AnomalyReport.empty())
    o.backtester_chief = MagicMock()
    o.backtester_chief.load_context.return_value = {}
    o.judgment_chief = MagicMock()
    o.judgment_chief.run = AsyncMock(return_value=result)
    o.conflict_agent = MagicMock()
    o.conflict_agent.run = AsyncMock(return_value=ConflictResolution(verdict="EXIT", reasoning="r"))
    return o


def _bottom_up():
    return NS(ticker="X", asset_class="equity")


def test_conflict_triggers_agent():
    res = _result(conflict=True)
    o = _orch(res)
    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.LONG))
    o.conflict_agent.run.assert_awaited_once()
    assert out.conflict_resolution.verdict == "EXIT"


def test_no_conflict_skips_agent():
    res = _result(conflict=False)
    o = _orch(res)
    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.NONE))
    o.conflict_agent.run.assert_not_awaited()
    assert out.conflict_resolution is None


def test_orchestrator_fills_short_thesis():
    """ShortThesisAgent wird nach dem Konflikt-Block aufgerufen und füllt short_thesis/short_xai."""
    from core.domain.models import ShortAction, ShortAssessment

    # DeepDiveResult mit gesetztem short_assessment (damit der Null-Schutz greift)
    sa = ShortAssessment(
        asset_class="equity",
        short_action=ShortAction.SHORT, confidence=0.62, archetypes=["distress"],
        thesis_flags=["Altman-Z 0.9"], regime_effect="tailwind",
        squeeze_risk="low", hard_to_borrow=False,
        suggested_size_pct=3.0, stop_pct=15.0,
    )
    res = _result(conflict=False)
    res.short_assessment = sa

    o = _orch(res)
    # ShortThesisAgent als Mock injizieren (wie ConflictAgent in _orch)
    o.short_thesis_agent = MagicMock()

    async def _fake_run(ticker, sa, ac):
        return ("T", "X")

    o.short_thesis_agent.run = _fake_run

    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.NONE))
    assert out.short_thesis == "T"
    assert out.short_xai == "X"


def test_orchestrator_skips_short_thesis_without_assessment():
    """Null-Schutz: ohne short_assessment (None) wird der ShortThesisAgent NICHT
    aufgerufen; die Felder bleiben leer (AGENTS.md §4: Fehlerpfade testen)."""
    res = _result(conflict=False)
    res.short_assessment = None
    o = _orch(res)
    o.short_thesis_agent = MagicMock()
    o.short_thesis_agent.run = AsyncMock(return_value=("T", "X"))

    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.NONE))
    o.short_thesis_agent.run.assert_not_awaited()
    assert out.short_thesis == ""
    assert out.short_xai == ""


def test_orchestrator_short_thesis_error_is_safe():
    """Wirft der ShortThesisAgent, läuft die Analyse stabil weiter und die Felder
    bleiben leer — kein Crash (AGENTS.md §4: Fehlerpfade testen)."""
    from core.domain.models import ShortAction, ShortAssessment

    sa = ShortAssessment(
        asset_class="equity",
        short_action=ShortAction.SHORT, confidence=0.62, archetypes=["distress"],
        thesis_flags=["Altman-Z 0.9"], regime_effect="tailwind",
        squeeze_risk="low", hard_to_borrow=False,
        suggested_size_pct=3.0, stop_pct=15.0,
    )
    res = _result(conflict=False)
    res.short_assessment = sa
    o = _orch(res)
    o.short_thesis_agent = MagicMock()
    o.short_thesis_agent.run = AsyncMock(side_effect=Exception("boom"))

    out = asyncio.run(o.run(cockpit=None, bottom_up=_bottom_up(), market="USA",
                            current_position=PositionState.NONE))
    assert out.short_thesis == ""
    assert out.short_xai == ""
