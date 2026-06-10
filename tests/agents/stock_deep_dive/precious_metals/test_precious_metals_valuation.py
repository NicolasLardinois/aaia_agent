import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.precious_metals.precious_metals_valuation_agent import PreciousMetalsValuationAgent
from core.domain.events import PreciousMetalsValuationReady, ValuationRangeReady


def _make_agent(real_rate: float, price: float = 2000.0) -> PreciousMetalsValuationAgent:
    macro = MagicMock()
    macro.get_extended_state.return_value = {"real_rate_10y": real_rate}
    market = MagicMock()
    market.get_current_price.return_value = price
    bus = MagicMock()
    return PreciousMetalsValuationAgent(macro, market, bus), bus


def test_positive_real_rate_does_not_invert_band():
    # Silver hat nur die Realzins-Methode — kein S2F/Inflation als Fallback
    agent, _ = _make_agent(real_rate=2.5)
    result = asyncio.run(agent.run("silver"))
    assert result.combined_low < result.combined_high, (
        f"Band invertiert: low={result.combined_low}, high={result.combined_high}"
    )


def test_negative_real_rate_does_not_invert_band():
    agent, _ = _make_agent(real_rate=-1.0)
    result = asyncio.run(agent.run("silver"))
    assert result.combined_low < result.combined_high


def test_publishes_precious_metals_event_not_equity_event():
    agent, bus = _make_agent(real_rate=0.5)
    asyncio.run(agent.run("gold"))
    published_types = [type(call_args[0][0]) for call_args in bus.publish.call_args_list]
    assert PreciousMetalsValuationReady in published_types
    assert ValuationRangeReady not in published_types
