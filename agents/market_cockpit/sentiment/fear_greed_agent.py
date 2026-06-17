import asyncio

from core.domain.events import FearGreedDataReady
from core.domain.models import FearGreedSnapshot, Signal, SignalStatus
from core.ports.data_provider import SentimentDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = FearGreedSnapshot(value=None, label="Unknown", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE)


def _label(value: float) -> str:
    if value <= 25:  return "Extreme Fear"
    if value <= 45:  return "Fear"
    if value <= 55:  return "Neutral"
    if value <= 75:  return "Greed"
    return "Extreme Greed"


def _signal(value: float | None) -> Signal:
    if value is None:
        return Signal.NEUTRAL
    # Contrarian, NUR in den Extremen robust (symmetrisch; Review D3)
    if value <= 25:
        return Signal.BULLISH    # Extreme Fear → Contrarian Kauf
    if value >= 75:
        return Signal.BEARISH    # Extreme Greed → Contrarian Vorsicht
    return Signal.NEUTRAL


class FearGreedAgent:
    def __init__(self, bus: EventBus, provider: SentimentDataProvider | None = None):
        self.bus = bus
        self.provider = provider

    async def run(self) -> FearGreedSnapshot:
        value = None
        if self.provider is not None:
            value = await asyncio.to_thread(self.provider.get_fear_greed)
        if value is None:
            self.bus.publish(FearGreedDataReady(source="fear_greed_agent", payload={"value": None, "label": "Unknown"}))
            return _DEFAULT
        label = _label(value)
        result = FearGreedSnapshot(value=value, label=label, signal=_signal(value), status=SignalStatus.AVAILABLE)
        self.bus.publish(FearGreedDataReady(source="fear_greed_agent", payload={"value": value, "label": label}))
        return result

    @staticmethod
    def default() -> FearGreedSnapshot:
        return _DEFAULT
