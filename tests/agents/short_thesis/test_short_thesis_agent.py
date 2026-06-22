import asyncio
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

from core.domain.models import ShortAction
from agents.short_thesis.short_thesis_agent import ShortThesisAgent


def _sa():
    return NS(short_action=ShortAction.SHORT, confidence=0.62, archetypes=["distress"],
              thesis_flags=["Altman-Z 0.9 (Konkurszone)"], regime_effect="tailwind",
              squeeze_risk="low", hard_to_borrow=False, suggested_size_pct=3.0, stop_pct=15.0)


def test_returns_thesis_and_xai():
    llm = MagicMock(); llm.complete.side_effect = ["THESE-TEXT", "XAI-TEXT"]
    thesis, xai = asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", _sa(), "equity"))
    assert thesis == "THESE-TEXT" and xai == "XAI-TEXT"
    assert llm.complete.call_count == 2
    assert "THESE-TEXT" in llm.complete.call_args_list[1][0][0]   # XAI-Prompt enthält die These


def test_none_assessment_returns_empty():
    llm = MagicMock()
    assert asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", None, "equity")) == ("", "")
    llm.complete.assert_not_called()


def test_llm_error_returns_empty():
    llm = MagicMock(); llm.complete.side_effect = Exception("boom")
    assert asyncio.run(ShortThesisAgent(llm, MagicMock()).run("AAPL", _sa(), "equity")) == ("", "")
