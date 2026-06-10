import asyncio
import statistics
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent, _combine_methods
from core.domain.models import ValuationMethod


def _make_agent(data: dict) -> ValuationRangeAgent:
    fundamentals = MagicMock()
    fundamentals.get_fundamentals.return_value = data
    market = MagicMock()
    market.get_current_price.return_value = data.get("current_price", 100.0)
    bus = MagicMock()
    return ValuationRangeAgent(fundamentals, market, bus)


def test_dcf_does_not_crash_when_wacc_equals_terminal_growth():
    agent = _make_agent({
        "current_price": 100.0,
        "fcf_per_share": 5.0,
        "wacc": 0.025,
        "revenue_cagr_3y": 10,
        "eps_trailing": 8.0,
    })
    result = asyncio.run(agent.run("AAPL"))
    assert result is not None


def test_band_aggregation_uses_median_not_extreme():
    methods = [
        ValuationMethod(name="KGV",       low=90.0,  high=130.0),
        ValuationMethod(name="EV/EBITDA", low=85.0,  high=120.0),
        ValuationMethod(name="DCF",       low=95.0,  high=125.0),
    ]
    low, high = _combine_methods(methods)
    assert low  == 90.0,  f"Expected median low 90.0, got {low}"
    assert high == 125.0, f"Expected median high 125.0, got {high}"
