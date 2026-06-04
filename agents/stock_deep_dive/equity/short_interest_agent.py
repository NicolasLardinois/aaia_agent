import asyncio

from core.domain.events import ShortInterestReady
from core.domain.models import ShortInterestSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL)


class ShortInterestAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> ShortInterestSnapshot:
        data = await asyncio.to_thread(self.provider.get_short_interest, ticker)
        short_float = data.get("short_float_pct")
        dtc = data.get("days_to_cover")
        signal = (
            Signal.BEARISH if (short_float or 0) > 20
            else Signal.BULLISH if (short_float or 100) < 5
            else Signal.NEUTRAL
        )
        result = ShortInterestSnapshot(short_float_pct=short_float, days_to_cover=dtc, signal=signal)
        self.bus.publish(ShortInterestReady(source="short_interest_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> ShortInterestSnapshot:
        return _DEFAULT
