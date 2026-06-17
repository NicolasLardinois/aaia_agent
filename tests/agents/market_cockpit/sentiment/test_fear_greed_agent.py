import asyncio
from unittest.mock import MagicMock

from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent, _signal, _label
from core.domain.models import Signal, SignalStatus


def test_extreme_fear_is_bullish():
    assert _signal(20.0) == Signal.BULLISH


def test_moderate_fear_is_neutral():
    # 40 (Fear) ist KEIN Extrem mehr → neutral (Review D3)
    assert _signal(40.0) == Signal.NEUTRAL


def test_extreme_greed_is_bearish():
    assert _signal(80.0) == Signal.BEARISH


def test_moderate_greed_is_neutral():
    assert _signal(65.0) == Signal.NEUTRAL


def test_label_unchanged():
    assert _label(20.0) == "Extreme Fear"
    assert _label(80.0) == "Extreme Greed"


def test_run_available_with_provider():
    provider = MagicMock()
    provider.get_fear_greed.return_value = 18.0
    agent = FearGreedAgent(MagicMock(), provider=provider)
    result = asyncio.run(agent.run())
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BULLISH


def test_run_unavailable_without_value():
    provider = MagicMock()
    provider.get_fear_greed.return_value = None
    agent = FearGreedAgent(MagicMock(), provider=provider)
    result = asyncio.run(agent.run())
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL
