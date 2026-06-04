import asyncio

from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent
from agents.market_cockpit.yield_curve.sovereign_spread_agent import SovereignSpreadAgent
from core.domain.events import YieldCurveChiefReady
from core.domain.models import YieldCurveChiefResult
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus


class YieldCurveChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.yield_spread_agent     = YieldSpreadAgent(macro, ecb, snb, bus)
        self.sovereign_spread_agent = SovereignSpreadAgent(ecb, bus)

    async def run(self) -> YieldCurveChiefResult:
        results = await asyncio.gather(
            self.yield_spread_agent.run(),
            self.sovereign_spread_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        yield_spreads     = _safe(results[0], YieldSpreadAgent.default())
        sovereign_spreads = _safe(results[1], SovereignSpreadAgent.default())

        self.bus.publish(YieldCurveChiefReady(source="yield_curve_chief_agent", payload={}))

        return YieldCurveChiefResult(
            yield_spreads=yield_spreads,
            sovereign_spreads=sovereign_spreads,
        )

    @staticmethod
    def default() -> YieldCurveChiefResult:
        return YieldCurveChiefResult(
            yield_spreads=YieldSpreadAgent.default(),
            sovereign_spreads=SovereignSpreadAgent.default(),
        )
