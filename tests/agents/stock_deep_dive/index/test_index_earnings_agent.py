import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.index.index_earnings_agent import IndexEarningsAgent, _signal
from core.domain.models import Signal, SignalStatus


def test_signal_strong_growth_and_up_revision_is_bullish():
    assert _signal(eps_growth=12.0, revision="up") == Signal.BULLISH


def test_signal_negative_growth_is_bearish():
    assert _signal(eps_growth=-12.0, revision="stable") == Signal.BEARISH


def test_signal_down_revision_is_bearish():
    assert _signal(eps_growth=5.0, revision="down") == Signal.BEARISH


def test_signal_mid_is_neutral():
    assert _signal(eps_growth=5.0, revision="stable") == Signal.NEUTRAL


def test_run_unavailable_without_index_fundamentals():
    provider = MagicMock()
    provider.get_index_fundamentals.return_value = {}
    agent = IndexEarningsAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL


def test_run_available_with_index_fundamentals():
    provider = MagicMock()
    provider.get_index_fundamentals.return_value = {
        "eps_ttm": 220.0, "eps_fwd": 245.0, "eps_growth_1y": 11.0,
        "revenue_growth_1y": 5.0, "operating_margin": 13.0, "estimate_revision": "up",
    }
    agent = IndexEarningsAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BULLISH
    assert result.estimate_revision == "up"
