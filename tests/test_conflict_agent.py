import asyncio
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

from agents.conflict.conflict_agent import ConflictAgent, _parse_verdict


class _LLM:
    def __init__(self, resp): self.resp = resp; self.last_prompt = None
    def complete(self, prompt, system):
        self.last_prompt = prompt
        return self.resp


def _rec():
    return NS(action=NS(value="HOLD"), reasoning="Long-These intakt.")


def _sa():
    return NS(short_action=NS(value="NONE"), confidence=0.72, archetypes=["distress"],
              thesis_flags=["Altman-Z 1.2 (Konkurszone)"])


def _run(resp, bt=None):
    agent = ConflictAgent(_LLM(resp), MagicMock())
    from core.domain.models import PositionState, AnomalyReport
    return agent, asyncio.run(agent.run(
        ticker="X", current_position=PositionState.LONG, recommendation=_rec(),
        short_assessment=_sa(), conflict_reason="Long gehalten, screent als Short",
        top_down_anomaly=AnomalyReport.empty(), bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context=bt))


def test_parses_verdict():
    assert _parse_verdict("VERDICT: EXIT\nGründe…") == "EXIT"
    assert _parse_verdict("verdict: reverse\n…") == "REVERSE"


def test_run_returns_resolution():
    _, cr = _run("VERDICT: EXIT\nDie These ist gekippt.")
    assert cr.verdict == "EXIT"
    assert "gekippt" in cr.reasoning


def test_parse_fallback_hold():
    _, cr = _run("Ich bin unsicher, keine klare Aussage.")
    assert cr.verdict == "HOLD"


def test_track_record_in_prompt():
    agent, _ = _run("VERDICT: HOLD\n…", bt={"hit_rate": 0.65})
    assert "65" in agent.llm.last_prompt or "0.65" in agent.llm.last_prompt
