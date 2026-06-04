import asyncio
from core.domain.events import PutCallDataReady
from core.domain.models import PutCallSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL)

# CBOE Total Put/Call Ratio (Yahoo Finance Ticker)
PUTCALL_TICKER = "^PCALL"


def _signal(ratio: float | None) -> Signal:
    if ratio is None:
        return Signal.NEUTRAL
    # Contrarian: hohes Ratio = viele Puts = Markt zu pessimistisch → BULLISH
    if ratio > 1.2:
        return Signal.BULLISH
    if ratio < 0.7:
        return Signal.BEARISH
    return Signal.NEUTRAL


class PutCallAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> PutCallSnapshot:
        ratio = await asyncio.to_thread(self.provider.get_current_price, PUTCALL_TICKER)
        if isinstance(ratio, Exception):
            ratio = None

        result = PutCallSnapshot(ratio=ratio, signal=_signal(ratio))
        self.bus.publish(PutCallDataReady(source="put_call_agent", payload={"ratio": ratio}))
        return result

    @staticmethod
    def default() -> PutCallSnapshot:
        return _DEFAULT
