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
