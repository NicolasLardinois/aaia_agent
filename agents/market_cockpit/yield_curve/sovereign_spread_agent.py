import asyncio
from core.domain.events import SovereignSpreadDataReady
from core.domain.models import SovereignSpreadSnapshot, Signal
from core.ports.data_provider import EcbDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL)


def _signal(btp_bund: float | None) -> Signal:
    if btp_bund is None:
        return Signal.NEUTRAL
    if btp_bund > 250:
        return Signal.BEARISH   # starker Eurozone-Stress
    if btp_bund > 150:
        return Signal.BEARISH   # erhöhter Stress
    return Signal.NEUTRAL


class SovereignSpreadAgent:
    def __init__(self, ecb: EcbDataProvider, bus: EventBus):
        self.ecb = ecb
        self.bus = bus

    async def run(self) -> SovereignSpreadSnapshot:
        yields = await asyncio.to_thread(self.ecb.get_sovereign_yields)
        if isinstance(yields, Exception):
            yields = {}

        de  = yields.get("DE_10y")
        it  = yields.get("IT_10y")
        fr  = yields.get("FR_10y")
        es  = yields.get("ES_10y")

        def _spread(country: float | None, bund: float | None) -> float | None:
            if country is None or bund is None:
                return None
            return round((country - bund) * 100, 1)  # in Basispunkten

        btp_bund   = _spread(it, de)
        oat_bund   = _spread(fr, de)
        bonos_bund = _spread(es, de)

        result = SovereignSpreadSnapshot(
            btp_bund=btp_bund, oat_bund=oat_bund, bonos_bund=bonos_bund,
            signal=_signal(btp_bund),
        )
        self.bus.publish(SovereignSpreadDataReady(source="sovereign_spread_agent", payload={
            "btp_bund": btp_bund, "oat_bund": oat_bund,
        }))
        return result

    @staticmethod
    def default() -> SovereignSpreadSnapshot:
        return _DEFAULT
