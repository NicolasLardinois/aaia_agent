import asyncio

from core.domain.events import CrossMetalReady
from core.domain.models import CrossMetalSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

# Historische Durchschnittswerte der Ratios
GOLD_SILVER_AVG    = 68.0   # historischer Durchschnitt ~65-70
GOLD_PLATINUM_AVG  = 1.0    # Gold/Platin historically nahe 1:1

_DEFAULT = CrossMetalSnapshot(
    gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL
)


def _ratio_signal(current: float, avg: float, high_is_bearish: bool = True) -> Signal:
    deviation = (current - avg) / avg
    if high_is_bearish:
        if deviation > 0.15:
            return Signal.BEARISH   # ratio sehr hoch → Silber/Platin günstig vs. Gold
        if deviation < -0.15:
            return Signal.BULLISH
    return Signal.NEUTRAL


class CrossMetalAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self) -> CrossMetalSnapshot:
        gold_price, silver_price, platinum_price = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, "GC=F"),
            asyncio.to_thread(self.provider.get_current_price, "SI=F"),
            asyncio.to_thread(self.provider.get_current_price, "PL=F"),
            return_exceptions=True,
        )

        gs_ratio = None
        gp_ratio = None

        if not isinstance(gold_price, Exception) and not isinstance(silver_price, Exception):
            if silver_price is not None and silver_price > 0:
                gs_ratio = round(gold_price / silver_price, 2)

        if not isinstance(gold_price, Exception) and not isinstance(platinum_price, Exception):
            if platinum_price is not None and platinum_price > 0:
                gp_ratio = round(gold_price / platinum_price, 2)

        signal = _ratio_signal(gs_ratio or GOLD_SILVER_AVG, GOLD_SILVER_AVG)

        result = CrossMetalSnapshot(
            gold_silver_ratio=gs_ratio,
            gold_platinum_ratio=gp_ratio,
            signal=signal,
        )
        self.bus.publish(CrossMetalReady(source="cross_metal_agent", payload={
            "gold_silver_ratio": gs_ratio,
            "gold_platinum_ratio": gp_ratio,
        }))
        return result

    @staticmethod
    def default() -> CrossMetalSnapshot:
        return _DEFAULT
