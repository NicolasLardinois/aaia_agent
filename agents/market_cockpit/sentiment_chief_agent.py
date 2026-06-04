import asyncio

from agents.market_cockpit.sentiment.vix_agent import VIXAgent
from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent
from agents.market_cockpit.sentiment.put_call_agent import PutCallAgent
from core.domain.events import SentimentChiefReady
from core.domain.models import SentimentChiefResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class SentimentChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus)
        self.put_call_agent   = PutCallAgent(market, bus)

    async def run(self) -> SentimentChiefResult:
        results = await asyncio.gather(
            self.vix_agent.run(),
            self.fear_greed_agent.run(),
            self.put_call_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        vix        = _safe(results[0], VIXAgent.default())
        fear_greed = _safe(results[1], FearGreedAgent.default())
        put_call   = _safe(results[2], PutCallAgent.default())

        self.bus.publish(SentimentChiefReady(source="sentiment_chief_agent", payload={}))

        return SentimentChiefResult(vix=vix, fear_greed=fear_greed, put_call=put_call)

    @staticmethod
    def default() -> SentimentChiefResult:
        return SentimentChiefResult(
            vix=VIXAgent.default(),
            fear_greed=FearGreedAgent.default(),
            put_call=PutCallAgent.default(),
        )
