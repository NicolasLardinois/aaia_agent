import asyncio

from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent
from agents.market_cockpit.yield_curve.sovereign_spread_agent import SovereignSpreadAgent
from core.domain.events import YieldCurveChiefReady
from core.domain.models import YieldCurveChiefResult, Signal, SignalStatus
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus
from core.utils.aggregation import weighted_signal

# US-Kurve als primärer Rezessionsprädiktor (NY-Fed-Modell); EU-Sovereign als Stress-Indikator
_WEIGHTS = {"us_curve": 0.60, "eu_sovereign": 0.40}


def _aggregate(items):
    return weighted_signal(items)


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

        # US-Status: UNAVAILABLE wenn kein Spread vorhanden
        usa_pt = yield_spreads.usa
        us_status = (
            SignalStatus.UNAVAILABLE
            if usa_pt.spread_10y2y is None and usa_pt.spread_10y3m is None
            else SignalStatus.AVAILABLE
        )

        # EU-Status: UNAVAILABLE wenn keine Spreads vorhanden
        eu_status = (
            SignalStatus.UNAVAILABLE
            if not sovereign_spreads.spreads_by_country
            else SignalStatus.AVAILABLE
        )

        items = [
            (usa_pt.signal,          _WEIGHTS["us_curve"],    us_status),
            (sovereign_spreads.signal, _WEIGHTS["eu_sovereign"], eu_status),
        ]
        overall, _ = _aggregate(items)

        self.bus.publish(YieldCurveChiefReady(source="yield_curve_chief_agent", payload={}))

        return YieldCurveChiefResult(
            yield_spreads=yield_spreads,
            sovereign_spreads=sovereign_spreads,
            signal=overall,
        )

    @staticmethod
    def default() -> YieldCurveChiefResult:
        return YieldCurveChiefResult(
            yield_spreads=YieldSpreadAgent.default(),
            sovereign_spreads=SovereignSpreadAgent.default(),
            signal=Signal.NEUTRAL,
            status=SignalStatus.UNAVAILABLE,
        )
