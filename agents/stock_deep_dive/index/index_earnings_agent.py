import asyncio

from core.domain.events import IndexEarningsReady
from core.domain.models import IndexEarningsSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexEarningsSnapshot(
    eps_growth_1y=None, revenue_growth_1y=None,
    operating_margin=None, estimate_revision="stable",
    signal=Signal.NEUTRAL,
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
        self.bus    = bus

    async def run(self, ticker: str) -> IndexEarningsSnapshot:
        try:
            info = await asyncio.to_thread(self.market.get_info, ticker)
            if isinstance(info, Exception) or not info:
                return _DEFAULT

            eps_g  = info.get("earningsGrowth")
            rev_g  = info.get("revenueGrowth")
            margin = info.get("operatingMargins")

            eps_g_pct  = round(eps_g  * 100, 2) if eps_g  is not None else None
            rev_g_pct  = round(rev_g  * 100, 2) if rev_g  is not None else None
            margin_pct = round(margin * 100, 2) if margin is not None else None

            # Estimate revision: infer from forward vs trailing PE change (proxy)
            fwd_pe  = info.get("forwardPE")
            trail_pe = info.get("trailingPE")
            if fwd_pe and trail_pe:
                revision = "up" if fwd_pe < trail_pe * 0.95 else ("down" if fwd_pe > trail_pe * 1.05 else "stable")
            else:
                revision = "stable"

            result = IndexEarningsSnapshot(
                eps_growth_1y=eps_g_pct,
                revenue_growth_1y=rev_g_pct,
                operating_margin=margin_pct,
                estimate_revision=revision,
                signal=_signal(eps_g_pct, revision),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexEarningsReady(source="index_earnings_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexEarningsSnapshot:
        return _DEFAULT
