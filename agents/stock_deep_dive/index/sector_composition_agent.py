import asyncio
from collections import defaultdict

from core.domain.events import SectorCompositionReady
from core.domain.models import SectorCompositionSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = SectorCompositionSnapshot(
    top_sector=None, top_sector_weight=None, top_holding=None, top_holding_weight=None,
    top_10_concentration=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

_HHI_HIGH = 2000.0   # > 2000 → konzentriert (US-DOJ-Schwelle für "highly concentrated")


def _hhi(holdings: list[dict]) -> float:
    return round(sum(float(h["weight_pct"]) ** 2 for h in holdings), 1)


def _concentration_signal(hhi: float) -> Signal:
    # hohe Konzentration = höheres idiosynkratisches Risiko → vorsichtiger (bearish-Tilt)
    if hhi > _HHI_HIGH:
        return Signal.BEARISH
    return Signal.NEUTRAL


class SectorCompositionAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus = bus

    async def run(self, ticker: str) -> SectorCompositionSnapshot:
        holdings = await asyncio.to_thread(self.market.get_index_holdings, ticker)
        if not holdings:
            self.bus.publish(SectorCompositionReady(source="sector_composition_agent", payload={"ticker": ticker}))
            return _DEFAULT

        by_sector: dict[str, float] = defaultdict(float)
        for h in holdings:
            by_sector[h.get("sector") or "Unknown"] += float(h["weight_pct"])
        top_sector, top_sector_w = max(by_sector.items(), key=lambda kv: kv[1])

        top = max(holdings, key=lambda h: float(h["weight_pct"]))
        top10 = round(sum(float(h["weight_pct"]) for h in holdings[:10]), 1)
        hhi = _hhi(holdings)

        result = SectorCompositionSnapshot(
            top_sector=top_sector, top_sector_weight=round(top_sector_w, 1),
            top_holding=top.get("name"), top_holding_weight=round(float(top["weight_pct"]), 1),
            top_10_concentration=top10,
            signal=_concentration_signal(hhi), status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(SectorCompositionReady(source="sector_composition_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SectorCompositionSnapshot:
        return _DEFAULT
