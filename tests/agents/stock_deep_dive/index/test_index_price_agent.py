import asyncio
from unittest.mock import MagicMock

import pandas as pd

from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent, _signal, _52w
from core.domain.models import Signal, SignalStatus


def _hist(values):
    idx = pd.date_range("2020-01-02", periods=len(values), freq="B")
    return pd.DataFrame({"Close": pd.Series(values, index=idx, dtype=float)})


def test_signal_strong_uptrend_is_bullish():
    assert _signal(perf_1y=20.0, perf_3m=4.0, dist_52w_high=-2.0) == Signal.BULLISH


def test_signal_deep_drawdown_is_bearish():
    assert _signal(perf_1y=-20.0, perf_3m=-5.0, dist_52w_high=-25.0) == Signal.BEARISH


def test_52w_from_history():
    values = [float(100 + i) for i in range(300)]
    high, low = _52w(_hist(values)["Close"])
    assert high == max(values[-252:])
    assert low == min(values[-252:])


def test_uses_total_return_when_available():
    provider = MagicMock()
    provider.get_total_return_history.return_value = _hist([float(100 + i) for i in range(300)])
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.high_52w is not None  # aus Historie, nicht info


def test_falls_back_to_price_return():
    provider = MagicMock()
    provider.get_total_return_history.return_value = None
    provider.get_price_history.return_value = _hist([float(100 + i) for i in range(300)])
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.current_price is not None


def test_unavailable_without_any_history():
    provider = MagicMock()
    provider.get_total_return_history.return_value = None
    provider.get_price_history.return_value = None
    provider.get_info.return_value = {}
    agent = IndexPriceAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE
