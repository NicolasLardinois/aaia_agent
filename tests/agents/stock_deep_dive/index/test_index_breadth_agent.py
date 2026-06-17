import asyncio
from unittest.mock import MagicMock

import pandas as pd

from agents.stock_deep_dive.index.index_breadth_agent import (
    IndexBreadthAgent, _signal, _breadth,
)
from core.domain.models import Signal, SignalStatus


def _series(values):
    idx = pd.date_range("2022-01-03", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_signal_high_breadth_is_bullish():
    assert _signal(pct_above_ma200=75.0) == Signal.BULLISH


def test_signal_low_breadth_is_bearish():
    assert _signal(pct_above_ma200=25.0) == Signal.BEARISH


def test_signal_mid_breadth_is_neutral():
    assert _signal(pct_above_ma200=50.0) == Signal.NEUTRAL


def test_breadth_counts_above_ma200():
    # 2 von 3 Titeln über ihrer MA200
    up = _series([float(100 + i) for i in range(260)])         # steigend → über MA200
    up2 = _series([float(100 + i) for i in range(260)])
    down = _series([float(360 - i) for i in range(260)])        # fallend → unter MA200
    stats = _breadth({"A": up, "B": up2, "C": down})
    assert stats["pct_above_ma200"] > 60.0
    assert stats["advance_decline_ratio"] is not None


def test_run_unavailable_when_no_constituents():
    provider = MagicMock()
    provider.get_constituent_histories.return_value = {}
    agent = IndexBreadthAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL


def test_run_available_with_constituents():
    provider = MagicMock()
    up = _series([float(100 + i) for i in range(260)])
    provider.get_constituent_histories.return_value = {"A": up, "B": up, "C": up}
    agent = IndexBreadthAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BULLISH
