import asyncio
import logging

from agents.market_cockpit.sentiment.vix_agent import VIXAgent
from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent
from agents.market_cockpit.sentiment.put_call_agent import PutCallAgent
from core.domain.events import SentimentChiefReady
from core.domain.models import SentimentChiefResult, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider, SentimentDataProvider
from core.ports.dated_history import DatedHistoryPort
from core.ports.event_bus import EventBus
from core.ports.put_call_source import PutCallSource
from core.utils.aggregation import weighted_signal
from core.utils.safe import safe_result

_log = logging.getLogger(__name__)

_WEIGHTS = {"vix": 0.45, "fear_greed": 0.25, "put_call": 0.30}


def _aggregate(items):
    return weighted_signal(items)


class SentimentChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus,
                 sentiment: SentimentDataProvider | None = None,
                 history: DatedHistoryPort | None = None,
                 put_call_source: PutCallSource | None = None):
        self.bus = bus
        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus, provider=sentiment)
        # Persistente Put/Call-Tagesreihe statt I/O-intensivem Refetch (siehe PutCallAgent);
        # die CBOE-Daten selbst kommen über den injizierten put_call_source-Port.
        self.put_call_agent   = PutCallAgent(market, bus, history=history, source=put_call_source)

    async def run(self) -> SentimentChiefResult:
        results = await asyncio.gather(
            self.vix_agent.run(),
            self.fear_greed_agent.run(),
            self.put_call_agent.run(),
            return_exceptions=True,
        )

        vix        = safe_result(results[0], default=VIXAgent.default(), label="SentimentChief: VIXAgent", logger=_log)
        fear_greed = safe_result(results[1], default=FearGreedAgent.default(), label="SentimentChief: FearGreedAgent", logger=_log)
        put_call   = safe_result(results[2], default=PutCallAgent.default(), label="SentimentChief: PutCallAgent", logger=_log)

        # Status aus Rohdaten ableiten; Fear&Greed ist Stub → UNAVAILABLE
        vix_status        = SignalStatus.UNAVAILABLE if (vix.vix is None and vix.vstoxx is None) else SignalStatus.AVAILABLE
        fear_greed_status = SignalStatus.UNAVAILABLE if fear_greed.value is None else SignalStatus.AVAILABLE
        put_call_status   = SignalStatus.UNAVAILABLE if put_call.ratio is None else SignalStatus.AVAILABLE

        items = [
            (vix.signal,        _WEIGHTS["vix"],        vix_status),
            (fear_greed.signal, _WEIGHTS["fear_greed"], fear_greed_status),
            (put_call.signal,   _WEIGHTS["put_call"],   put_call_status),
        ]
        overall, _ = _aggregate(items)

        self.bus.publish(SentimentChiefReady(source="sentiment_chief_agent", payload={}))

        return SentimentChiefResult(
            vix=vix, fear_greed=fear_greed, put_call=put_call, signal=overall,
        )

    @staticmethod
    def default() -> SentimentChiefResult:
        return SentimentChiefResult(
            vix=VIXAgent.default(),
            fear_greed=FearGreedAgent.default(),
            put_call=PutCallAgent.default(),
            signal=Signal.NEUTRAL,
            status=SignalStatus.UNAVAILABLE,
        )
