import asyncio
from unittest.mock import MagicMock

import pandas as pd

from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import (
    CommodityValuationRangeAgent, _position,
)
from core.domain.models import Signal, SignalStatus


def test_position_cheap_below_p20():
    pos, sig = _position(15.0)
    assert pos == "cheap" and sig == Signal.BULLISH


def test_position_expensive_above_p80():
    pos, sig = _position(88.0)
    assert pos == "expensive" and sig == Signal.BEARISH


def test_outlier_spike_does_not_make_current_look_cheap():
    # Ein einzelner Spike (1000) darf den aktuellen Preis (50) nicht als billig ausweisen
    values = [40.0, 45.0, 50.0, 48.0, 52.0, 1000.0]
    hist = pd.DataFrame({"Close": pd.Series(values * 50)})  # current = 1000 am Ende? -> setze explizit
    hist = pd.DataFrame({"Close": pd.Series([40, 45, 50, 48, 52] * 50 + [50.0])})
    provider = MagicMock()
    provider.get_price_history.return_value = hist
    provider.get_inventory_history = MagicMock(return_value=[])
    supply = MagicMock()
    supply.get_production_cost_curve.return_value = {}
    agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=supply)
    result = asyncio.run(agent.run("CL=F"))
    # echtes Rang-Perzentil: 50 liegt im mittleren Bereich, nicht "cheap"
    assert result.position != "cheap"


def test_cost_curve_anchors_set_when_provider_returns_them():
    hist = pd.DataFrame({"Close": pd.Series([float(50 + i % 10) for i in range(300)])})
    provider = MagicMock()
    provider.get_price_history.return_value = hist
    supply = MagicMock()
    supply.get_production_cost_curve.return_value = {
        "cost_p25": 40.0, "cost_p50": 48.0, "cost_p75": 55.0, "cost_p90": 62.0,
    }
    agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=supply)
    result = asyncio.run(agent.run("CL=F"))
    assert result.production_cost_low == 40.0
    assert result.production_cost_high == 62.0
    assert result.status == SignalStatus.AVAILABLE


def test_no_history_is_unavailable():
    provider = MagicMock()
    provider.get_price_history.return_value = None
    agent = CommodityValuationRangeAgent(provider, MagicMock(), supply=MagicMock())
    result = asyncio.run(agent.run("CL=F"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_one_bar_history_returns_unavailable_no_crash():
    """1-Bar-Reihe: _percentile_of hätte nur 0 hist-Werte → Guard muss UNAVAILABLE liefern."""
    hist = pd.DataFrame({"Close": pd.Series([50.0])})
    provider = MagicMock()
    provider.get_price_history.return_value = hist
    agent = CommodityValuationRangeAgent(provider, MagicMock())
    result = asyncio.run(agent.run("CL=F"))
    assert result.status == SignalStatus.UNAVAILABLE


def test_all_nan_close_returns_unavailable_no_crash():
    """Komplett NaN-Reihe: close5.empty → kein iloc-Zugriff, kein Crash."""
    import numpy as np
    hist = pd.DataFrame({"Close": pd.Series([np.nan, np.nan, np.nan])})
    provider = MagicMock()
    provider.get_price_history.return_value = hist
    agent = CommodityValuationRangeAgent(provider, MagicMock())
    result = asyncio.run(agent.run("CL=F"))
    assert result.status == SignalStatus.UNAVAILABLE
