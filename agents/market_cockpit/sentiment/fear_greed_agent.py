import asyncio
from core.domain.events import FearGreedDataReady
from core.domain.models import FearGreedSnapshot, Signal
from core.ports.event_bus import EventBus

_DEFAULT = FearGreedSnapshot(value=None, label="Unknown", signal=Signal.NEUTRAL)


def _label(value: float) -> str:
    if value <= 25:  return "Extreme Fear"
    if value <= 45:  return "Fear"
    if value <= 55:  return "Neutral"
    if value <= 75:  return "Greed"
    return "Extreme Greed"


def _signal(value: float | None) -> Signal:
    if value is None:
        return Signal.NEUTRAL
    # Contrarian: Extreme Fear → Kaufgelegenheit, Extreme Greed → Vorsicht
    if value <= 25:  return Signal.BULLISH
    if value <= 45:  return Signal.BULLISH
    if value >= 75:  return Signal.BEARISH
    if value >= 55:  return Signal.BEARISH
    return Signal.NEUTRAL


async def _fetch_fear_greed() -> float | None:
    # TODO: CNN Fear & Greed API anbinden
    # URL: https://production.dataviz.cnn.io/index/fearandgreed/graphdata/
    return None


class FearGreedAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def run(self) -> FearGreedSnapshot:
        value = await _fetch_fear_greed()
        label = _label(value) if value is not None else "Unknown"
        result = FearGreedSnapshot(value=value, label=label, signal=_signal(value))
        self.bus.publish(FearGreedDataReady(source="fear_greed_agent", payload={"value": value, "label": label}))
        return result

    @staticmethod
    def default() -> FearGreedSnapshot:
        return _DEFAULT
