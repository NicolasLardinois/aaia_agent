import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.commodity.supply_demand_agent import (
    SupplyDemandAgent, _signal, _inventory_stats,
)
from core.domain.models import Signal, SignalStatus


def test_low_inventory_is_bullish():
    assert _signal(pct_vs_avg=-15.0) == Signal.BULLISH


def test_high_inventory_is_bearish():
    assert _signal(pct_vs_avg=25.0) == Signal.BEARISH


def test_normal_inventory_is_neutral():
    assert _signal(pct_vs_avg=5.0) == Signal.NEUTRAL


def test_inventory_stats_computes_pct_vs_avg():
    hist = [{"date": f"2020-{(i % 12) + 1:02d}-01", "inventory": 100.0} for i in range(60)]
    hist.append({"date": "2025-01-01", "inventory": 80.0})
    cur, avg5, pct = _inventory_stats(hist)
    assert cur == 80.0
    assert pct < 0  # aktuell unter dem 5J-Schnitt


def test_run_unavailable_without_inventory():
    supply = MagicMock()
    supply.get_inventory_history.return_value = []
    agent = SupplyDemandAgent(supply, MagicMock())
    result = asyncio.run(agent.run("CL=F"))
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL


def test_run_available_with_inventory():
    supply = MagicMock()
    hist = [{"date": f"2020-{(i % 12) + 1:02d}-01", "inventory": 100.0} for i in range(60)]
    hist.append({"date": "2025-01-01", "inventory": 70.0})
    supply.get_inventory_history.return_value = hist
    agent = SupplyDemandAgent(supply, MagicMock())
    result = asyncio.run(agent.run("CL=F"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BULLISH
