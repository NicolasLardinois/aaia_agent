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


def test_real_rate_method_is_price_independent():
    """Gleicher Realzins -> gleiche Realzins-Methoden-Range, unabhängig vom aktuellen Preis."""
    agent_low,  _ = _make_agent(real_rate=1.0, price=1500.0)
    agent_high, _ = _make_agent(real_rate=1.0, price=3000.0)
    r_low  = asyncio.run(agent_low.run("gold"))
    r_high = asyncio.run(agent_high.run("gold"))
    m_low  = next(m for m in r_low.methods  if m.name == "Realzins-Modell")
    m_high = next(m for m in r_high.methods if m.name == "Realzins-Modell")
    assert m_low.low == m_high.low
    assert m_low.high == m_high.high


def test_no_1200_inflation_method():
    agent, _ = _make_agent(real_rate=0.5)
    result = asyncio.run(agent.run("gold"))
    names = [m.name for m in result.methods]
    assert not any("Inflationsbereinigt" in n for n in names)


def test_combined_band_is_not_minmax_union():
    """Kombination konvergiert (gewichteter Median), nicht Union der Extreme."""
    agent, _ = _make_agent(real_rate=0.5, price=2000.0)
    result = asyncio.run(agent.run("gold"))
    method_lows  = [m.low  for m in result.methods]
    method_highs = [m.high for m in result.methods]
    if len(result.methods) >= 2:
        assert result.combined_low  >= min(method_lows)
        assert result.combined_high <= max(method_highs)
        # echte Konvergenz: nicht beide Extreme gleichzeitig
        assert not (result.combined_low == min(method_lows) and result.combined_high == max(method_highs))


def test_current_aisc_floor_updated():
    agent, _ = _make_agent(real_rate=0.5)
    result = asyncio.run(agent.run("gold"))
    aisc = next((m for m in result.methods if "AISC" in m.name or "Produktionskosten" in m.name), None)
    assert aisc is not None
    assert aisc.low >= 1200.0   # aktualisierter AISC-Median, nicht 1050
