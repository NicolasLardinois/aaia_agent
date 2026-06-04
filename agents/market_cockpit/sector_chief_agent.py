import asyncio

from agents.market_cockpit.sector.sector_performance_agent import SectorPerformanceAgent
from agents.market_cockpit.sector.sector_rotation_agent import SectorRotationAgent
from core.domain.events import SectorChiefReady
from core.domain.models import MarketRegime, SectorChiefResult, SectorRotationSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT_ROTATION = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)


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
            rotation = self.sector_rotation_agent.run(regime, performance.leading_usa)
        except Exception:
            rotation = SectorRotationAgent.default()

        self.bus.publish(SectorChiefReady(source="sector_chief_agent", payload={"regime": regime.value}))

        return SectorChiefResult(performance=performance, rotation=rotation)

    @staticmethod
    def default() -> SectorChiefResult:
        return SectorChiefResult(
            performance=SectorPerformanceAgent.default(),
            rotation=_DEFAULT_ROTATION,
        )
