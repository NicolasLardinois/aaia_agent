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
from core.domain.models import Signal, SignalStatus
from core.ports.data_provider import SentimentDataProvider


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


def test_index_chief_runs_with_empty_providers():
    """IndexChiefAgent: alle neuen Port-Methoden mit Default-Implementations
    → kein Absturz, UNAVAILABLE für fehlende Daten."""
    market = MagicMock()
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


def test_sentiment_chief_uses_injected_fear_greed_provider():
    """SentimentChiefAgent reicht den injizierten Provider an den FearGreedAgent
    durch → Extreme-Fear-Wert 10 ergibt BULLISH (contrarian) und AVAILABLE."""
    class _FakeSentiment(SentimentDataProvider):
        def get_fear_greed(self):
            return 10.0
    market = MagicMock()
    market.get_current_price.return_value = None
    bus = MagicMock()
    chief = SentimentChiefAgent(market, bus, sentiment=_FakeSentiment())
    result = asyncio.run(chief.run())
    assert result.fear_greed.value == 10.0
    assert result.fear_greed.signal == Signal.BULLISH
    assert result.fear_greed.status == SignalStatus.AVAILABLE


def test_top_down_orchestrator_threads_sentiment_provider():
    """TopDownOrchestrator reicht den sentiment-Provider bis zum FearGreedAgent durch."""
    from orchestrators.top_down_orchestrator import TopDownOrchestrator
    fake = MagicMock()
    orch = TopDownOrchestrator(
        macro=MagicMock(), ecb=MagicMock(), snb=MagicMock(),
        market=MagicMock(), bus=MagicMock(), sentiment=fake,
    )
    assert orch.sentiment_chief.fear_greed_agent.provider is fake
