import asyncio
from core.domain.events import BondSpreadReady
from core.domain.models import BondSpreadSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)


def _signal(spread_bps: float | None, trend: str) -> Signal:
    if spread_bps is None:
        return Signal.NEUTRAL
    if trend == "tightening":
        return Signal.BULLISH
    if trend == "widening":
        return Signal.BEARISH
    return Signal.NEUTRAL


class BondSpreadAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str) -> BondSpreadSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        spread_bps = data.get("spread_bps")
        oas        = data.get("oas")
        z_spread   = data.get("z_spread")
        trend      = data.get("spread_trend", "stable")

        result = BondSpreadSnapshot(
            spread_bps=spread_bps, oas=oas, z_spread=z_spread,
            spread_trend=trend, signal=_signal(spread_bps, trend),
        )
        self.bus.publish(BondSpreadReady(source="bond_spread_agent", payload={
            "ticker": ticker, "spread_bps": spread_bps, "trend": trend,
        }))
        return result

    @staticmethod
    def default() -> BondSpreadSnapshot:
        return _DEFAULT
