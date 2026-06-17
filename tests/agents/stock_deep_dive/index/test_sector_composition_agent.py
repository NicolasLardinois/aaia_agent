import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.index.sector_composition_agent import (
    SectorCompositionAgent, _hhi, _concentration_signal,
)
from core.domain.models import Signal, SignalStatus


def test_hhi_equal_weights():
    # 10 gleich gewichtete Titel à 10 % → HHI = 10 * 10^2 = 1000
    holdings = [{"name": f"T{i}", "weight_pct": 10.0, "sector": "X"} for i in range(10)]
    assert _hhi(holdings) == 1000.0


def test_hhi_concentrated_is_higher():
    holdings = [{"name": "Big", "weight_pct": 50.0, "sector": "X"}] + \
               [{"name": f"T{i}", "weight_pct": 5.0, "sector": "Y"} for i in range(10)]
    assert _hhi(holdings) > 2000.0


def test_concentration_signal_high_is_bearish():
    assert _concentration_signal(hhi=2500.0) == Signal.BEARISH


def test_concentration_signal_low_is_neutral():
    assert _concentration_signal(hhi=800.0) == Signal.NEUTRAL


def test_run_unavailable_without_holdings():
    provider = MagicMock()
    provider.get_index_holdings.return_value = []
    agent = SectorCompositionAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_run_available_computes_top10_and_top_sector():
    provider = MagicMock()
    provider.get_index_holdings.return_value = [
        {"name": "Apple", "weight_pct": 7.0, "sector": "Technology"},
        {"name": "Microsoft", "weight_pct": 6.0, "sector": "Technology"},
        {"name": "Nvidia", "weight_pct": 5.0, "sector": "Technology"},
    ] + [{"name": f"T{i}", "weight_pct": 1.0, "sector": "Financials"} for i in range(10)]
    agent = SectorCompositionAgent(provider, MagicMock())
    result = asyncio.run(agent.run("^GSPC"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.top_sector == "Technology"
    assert result.top_holding == "Apple"
    assert result.top_10_concentration is not None
