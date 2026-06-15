import asyncio
from core.domain.events import InflationDataReady
from core.domain.models import InflationSnapshot, InflationDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = InflationDataPoint(cpi=None, core_cpi=None, pce=None, ppi=None, real_rate_10y=None, signal=Signal.NEUTRAL)
_DEFAULT = InflationSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


_USA_EU = {"low": 1.0, "high": 3.0, "bearish": 4.0}
_CH     = {"low": 0.5, "high": 2.0, "bearish": 3.0}


def _signal(
    cpi: float | None,
    core_cpi: float | None = None,
    ppi: float | None = None,
    region: str = "usa",
    trend: str = "stable",   # reserviert: "rising"|"falling"|"stable" (benötigt CPI-Historie)
) -> Signal:
    if cpi is None:
        return Signal.NEUTRAL

    thr = _CH if region == "ch" else _USA_EU

    if cpi < 0.0:
        sig = Signal.BEARISH
    elif cpi < thr["low"]:
        sig = Signal.NEUTRAL
    elif cpi <= thr["high"]:
        sig = Signal.BULLISH
    elif cpi >= thr["bearish"]:
        sig = Signal.BEARISH
    else:
        sig = Signal.NEUTRAL   # erhöht aber nicht kritisch

    # Core CPI: BEARISH abschwächen wenn Kerninflation im Zielbereich (transiente Inflation)
    if sig == Signal.BEARISH and core_cpi is not None and core_cpi <= thr["high"]:
        sig = Signal.NEUTRAL

    # PPI: NEUTRAL verstärken wenn Erzeugerpreise Pipeline-Inflation anzeigen
    if sig == Signal.NEUTRAL and ppi is not None and ppi >= thr["bearish"]:
        sig = Signal.BEARISH

    return sig


class InflationAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> InflationSnapshot:
        state, ext, ecb_cpi, ecb_core, ecb_ppi, snb_cpi, snb_core = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_cpi),
            asyncio.to_thread(self.ecb.get_core_cpi),
            asyncio.to_thread(self.ecb.get_ppi),
            asyncio.to_thread(self.snb.get_cpi),
            asyncio.to_thread(self.snb.get_core_cpi),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        state    = _safe(state) or {}
        ext      = _safe(ext)   or {}
        ecb_cpi  = _safe(ecb_cpi)
        ecb_core = _safe(ecb_core)
        ecb_ppi  = _safe(ecb_ppi)
        snb_cpi  = _safe(snb_cpi)
        snb_core = _safe(snb_core)

        usa_cpi = state.get("inflation")
        usa_ppi = ext.get("ppi")
        usa = InflationDataPoint(
            cpi=usa_cpi,
            core_cpi=None,           # TODO: FRED CPILFESL via extended_state
            pce=None,                # TODO: FRED PCEPI via extended_state
            ppi=usa_ppi,
            real_rate_10y=ext.get("real_rate_10y"),
            signal=_signal(usa_cpi, ppi=usa_ppi, region="usa"),
        )
        eu = InflationDataPoint(
            cpi=ecb_cpi, core_cpi=ecb_core, pce=None,
            ppi=ecb_ppi, real_rate_10y=None,
            signal=_signal(ecb_cpi, core_cpi=ecb_core, ppi=ecb_ppi, region="eu"),
        )
        ch = InflationDataPoint(
            cpi=snb_cpi, core_cpi=snb_core, pce=None,
            ppi=None, real_rate_10y=None,
            signal=_signal(snb_cpi, core_cpi=snb_core, region="ch"),
        )
        result = InflationSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(InflationDataReady(source="inflation_agent", payload={
            "usa_cpi": usa.cpi, "eu_cpi": ecb_cpi, "ch_cpi": snb_cpi,
        }))
        return result

    @staticmethod
    def default() -> InflationSnapshot:
        return _DEFAULT
