"""
Task 13 Smoke-Tests: Chiefs mit Fake-Providern instanziieren und run() ohne
Exception durchlaufen. Prüft, dass alle geänderten Konstruktoren verdrahtet
sind und UNAVAILABLE-Sub-Snapshots korrekt geliefert werden.
"""
import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from adapters.data.sentiment_stub import SentimentStubProvider
from core.domain.models import SignalStatus


def test_commodity_chief_mikro_runs_without_supply_provider():
    """CommodityChiefAgentMikro: SupplyDemandAgent + COTAgent mit None-Provider
    → kein Absturz, UNAVAILABLE für fehlende Daten."""
    market = MagicMock()
    market.get_price_history.return_value = None
    bus = MagicMock()
    chief = CommodityChiefAgentMikro(market, bus)
    result = asyncio.run(chief.run("CL=F"))
    assert result is not None
    assert result.supply_demand.status == SignalStatus.UNAVAILABLE
    assert result.cot.status == SignalStatus.UNAVAILABLE


def test_sentiment_chief_runs_without_fear_greed_provider():
    """SentimentChiefAgent: FearGreedAgent ohne Provider → kein Absturz,
    fear_greed.value == None."""
    market = MagicMock()
    market.get_current_price.return_value = None
    bus = MagicMock()
    chief = SentimentChiefAgent(market, bus)
    result = asyncio.run(chief.run())
    assert result is not None
    assert result.fear_greed.value is None


def test_sentiment_stub_provider_returns_none():
    """SentimentStubProvider: Stub liefert None → FearGreedAgent UNAVAILABLE."""
    stub = SentimentStubProvider()
    assert stub.get_fear_greed() is None


def test_index_chief_runs_with_empty_providers():
    """IndexChiefAgent: alle neuen Port-Methoden mit Default-Implementations
    → kein Absturz, UNAVAILABLE für fehlende Daten."""
    market = MagicMock()
    market.get_total_return_history.return_value = None
    market.get_price_history.return_value = None
    market.get_info.return_value = {}
    market.get_constituent_histories.return_value = {}
    market.get_index_fundamentals.return_value = {}
    market.get_index_holdings.return_value = []
    bus = MagicMock()
    chief = IndexChiefAgent(market, bus)
    result = asyncio.run(chief.run("^GSPC"))
    assert result is not None
    assert result.price.status == SignalStatus.UNAVAILABLE
    assert result.breadth.status == SignalStatus.UNAVAILABLE
    assert result.earnings.status == SignalStatus.UNAVAILABLE
    assert result.composition.status == SignalStatus.UNAVAILABLE
