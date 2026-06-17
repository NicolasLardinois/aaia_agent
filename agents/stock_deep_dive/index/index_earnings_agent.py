import asyncio

from core.domain.events import IndexEarningsReady
from core.domain.models import IndexEarningsSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexEarningsSnapshot(
    eps_growth_1y=None, revenue_growth_1y=None, operating_margin=None,
    estimate_revision="stable", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)


def _signal(eps_growth: float | None, revision: str) -> Signal:
    if eps_growth is None:
        return Signal.NEUTRAL
    if eps_growth > 10 and revision == "up":
        return Signal.BULLISH
    if eps_growth < -10 or revision == "down":
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexEarningsAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus = bus

    async def run(self, ticker: str) -> IndexEarningsSnapshot:
        data = await asyncio.to_thread(self.market.get_index_fundamentals, ticker)
        if not data:
            self.bus.publish(IndexEarningsReady(source="index_earnings_agent", payload={"ticker": ticker}))
            return _DEFAULT

        eps_g = data.get("eps_growth_1y")
        revision = data.get("estimate_revision", "stable")
        result = IndexEarningsSnapshot(
            eps_growth_1y=round(eps_g, 2) if eps_g is not None else None,
            revenue_growth_1y=data.get("revenue_growth_1y"),
            operating_margin=data.get("operating_margin"),
            estimate_revision=revision,
            signal=_signal(eps_g, revision),
            status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(IndexEarningsReady(source="index_earnings_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexEarningsSnapshot:
        return _DEFAULT
