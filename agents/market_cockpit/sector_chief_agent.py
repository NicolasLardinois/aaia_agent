import asyncio

from agents.market_cockpit.sector.sector_performance_agent import SectorPerformanceAgent
from agents.market_cockpit.sector.sector_rotation_agent import SectorRotationAgent
from core.domain.events import SectorChiefReady
from core.domain.models import MarketRegime, SectorChiefResult, SectorRotationSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT_ROTATION = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)


def _top_sectors(performance, n: int = 3) -> list[str]:
    """Kombinierte Top-N-Sektoren über USA UND Eurozone (EU war zuvor ignoriert)."""
    merged: dict[str, float] = {}
    for region in (performance.usa or {}, performance.eurozone or {}):
        for name, ret in region.items():
            merged[name] = max(merged.get(name, float("-inf")), ret)
    return sorted(merged, key=merged.get, reverse=True)[:n]


class SectorChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.sector_performance_agent = SectorPerformanceAgent(market, bus)
        self.sector_rotation_agent    = SectorRotationAgent(bus)

    async def run(self, regime: MarketRegime) -> SectorChiefResult:
        performance_result = await asyncio.gather(
            self.sector_performance_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        performance = _safe(performance_result[0], SectorPerformanceAgent.default())

        try:
            top = _top_sectors(performance, n=3)
            rotation = self.sector_rotation_agent.run(regime, top)
        except Exception:
            rotation = SectorRotationAgent.default()

        self.bus.publish(SectorChiefReady(source="sector_chief_agent", payload={"regime": regime.value}))

        return SectorChiefResult(performance=performance, rotation=rotation)

    @staticmethod
    def default() -> SectorChiefResult:
        return SectorChiefResult(
            performance=SectorPerformanceAgent.default(),
            rotation=_DEFAULT_ROTATION,
            status=SignalStatus.UNAVAILABLE,
        )
