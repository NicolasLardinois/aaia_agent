import asyncio
from core.domain.events import GDPDataReady
from core.domain.models import GDPSnapshot, GDPDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = GDPDataPoint(
    gdp_growth=None, industrial_production=None,
    unemployment=None, consumer_sentiment=None, pmi=None, signal=Signal.NEUTRAL,
)
_DEFAULT = GDPSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(gdp: float | None, pmi: float | None, unemployment: float | None) -> Signal:
    score = 0
    if gdp is not None:
        score += 1 if gdp > 2.0 else (-1 if gdp < 0 else 0)
    if pmi is not None:
        score += 1 if pmi > 52 else (-1 if pmi < 48 else 0)
    if unemployment is not None:
        score += 1 if unemployment < 5.0 else (-1 if unemployment > 8.0 else 0)
    return Signal.BULLISH if score >= 2 else (Signal.BEARISH if score <= -2 else Signal.NEUTRAL)


class GDPAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> GDPSnapshot:
        state, ecb_gdp, ecb_ind, ecb_unemp, ecb_pmi, snb_gdp, snb_unemp = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.ecb.get_gdp_growth),
            asyncio.to_thread(self.ecb.get_unemployment),  # using unemployment as proxy
            asyncio.to_thread(self.ecb.get_unemployment),
            asyncio.to_thread(self.ecb.get_pmi),
            asyncio.to_thread(self.snb.get_gdp_growth),
            asyncio.to_thread(self.snb.get_unemployment),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        state      = _safe(state) or {}
        ecb_gdp    = _safe(ecb_gdp)
        ecb_ind    = _safe(ecb_ind)
        ecb_unemp  = _safe(ecb_unemp)
        ecb_pmi    = _safe(ecb_pmi)
        snb_gdp    = _safe(snb_gdp)
        snb_unemp  = _safe(snb_unemp)

        usa = GDPDataPoint(
            gdp_growth=state.get("gdp_growth"),
            industrial_production=state.get("industrial_production"),
            unemployment=state.get("unemployment"),
            consumer_sentiment=state.get("consumer_sentiment"),
            pmi=None,   # TODO: ISM Manufacturing via FRED/ISM
            signal=_signal(state.get("gdp_growth"), None, state.get("unemployment")),
        )
        eu = GDPDataPoint(
            gdp_growth=ecb_gdp, industrial_production=None,
            unemployment=ecb_unemp, consumer_sentiment=None,
            pmi=ecb_pmi,
            signal=_signal(ecb_gdp, ecb_pmi, ecb_unemp),
        )
        ch = GDPDataPoint(
            gdp_growth=snb_gdp, industrial_production=None,
            unemployment=snb_unemp, consumer_sentiment=None,
            pmi=None,   # TODO: procure.ch PMI
            signal=_signal(snb_gdp, None, snb_unemp),
        )
        result = GDPSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(GDPDataReady(source="gdp_agent", payload={
            "usa_gdp": usa.gdp_growth, "eu_gdp": ecb_gdp, "ch_gdp": snb_gdp,
        }))
        return result

    @staticmethod
    def default() -> GDPSnapshot:
        return _DEFAULT
