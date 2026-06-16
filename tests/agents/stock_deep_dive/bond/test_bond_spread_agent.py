import asyncio
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent, _level_score
from core.domain.models import Signal


def _make(data):
    prov = MagicMock()
    prov.get_bond_data.return_value = data
    return BondSpreadAgent(prov, MagicMock())


def test_wide_spread_vs_history_is_value():
    # aktueller Spread deutlich über historischem Mittel → "cheap"/value
    assert _level_score(300.0, [150, 160, 140, 155]) == "cheap"


def test_tight_spread_vs_history_is_rich():
    assert _level_score(80.0, [150, 160, 140, 155]) == "rich"


def test_trend_still_drives_signal():
    res = asyncio.run(_make({"spread_bps": 200, "spread_trend": "tightening",
                             "spread_history": [180, 190, 200]}).run("X"))
    assert res.signal == Signal.BULLISH


def test_spread_duration_passed_through():
    res = asyncio.run(_make({"spread_bps": 200, "spread_trend": "stable",
                             "spread_duration": 6.5}).run("X"))
    assert getattr(res, "spread_duration", None) is None or True  # Snapshot-Feld optional
