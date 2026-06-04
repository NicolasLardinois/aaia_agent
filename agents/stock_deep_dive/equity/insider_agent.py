import asyncio

from core.domain.events import InsiderDataReady
from core.domain.models import InsiderSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = InsiderSnapshot(net_direction="neutral", recent_transactions=0, signal=Signal.NEUTRAL)


class InsiderAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> InsiderSnapshot:
        transactions = await asyncio.to_thread(self.provider.get_insider_activity, ticker)
        buys  = sum(1 for t in transactions if t.get("type") == "buy")
        sells = sum(1 for t in transactions if t.get("type") == "sell")
        if buys > sells * 1.5:
            direction, signal = "net_buy", Signal.BULLISH
        elif sells > buys * 1.5:
            direction, signal = "net_sell", Signal.BEARISH
        else:
            direction, signal = "neutral", Signal.NEUTRAL
        result = InsiderSnapshot(net_direction=direction, recent_transactions=len(transactions), signal=signal)
        self.bus.publish(InsiderDataReady(source="insider_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> InsiderSnapshot:
        return _DEFAULT
