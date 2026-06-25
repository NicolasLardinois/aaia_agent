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
    trend: str = "stable",          # "rising" | "falling" | "stable"
    real_rate_10y: float | None = None,
) -> Signal:
    if cpi is None:
        return Signal.NEUTRAL

    thr = _CH if region == "ch" else _USA_EU

    # Lückenlose Bänder: jeder Wert fällt in genau eine Klasse.
    if cpi < 0.0:
        sig = Signal.BEARISH                         # Deflation
    elif cpi < thr["low"]:
        sig = Signal.NEUTRAL                         # unter Ziel, keine Deflation
    elif cpi <= thr["high"]:
        sig = Signal.BULLISH                         # Zielzone
    elif cpi < thr["bearish"]:
        sig = Signal.BEARISH                         # erhöht (3–4%) — vormals blinde Lücke
    else:
        sig = Signal.BEARISH                         # klar über Ziel

    # Core-Abschwächung (transiente Inflation)
    if sig == Signal.BEARISH and core_cpi is not None and core_cpi <= thr["high"]:
        sig = Signal.NEUTRAL

    # Trend-Modifikator: über Ziel + fallend → entschärfen
    if sig == Signal.BEARISH and cpi > thr["high"] and trend == "falling":
        sig = Signal.NEUTRAL

    # PPI Pipeline-Inflation verstärkt NEUTRAL → BEARISH
    if sig == Signal.NEUTRAL and ppi is not None and ppi >= thr["bearish"]:
        sig = Signal.BEARISH

    # Realzins-Gegenwind: hoher Realzins drückt Bewertungen
    if real_rate_10y is not None and real_rate_10y > 2.0 and sig != Signal.BEARISH:
        sig = Signal.BEARISH

    return sig


class InflationAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> InflationSnapshot:
        state, ext, ecb_cpi, ecb_core, ecb_ppi, ecb_10y, snb_cpi, snb_core = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_cpi),
            asyncio.to_thread(self.ecb.get_core_cpi),
            asyncio.to_thread(self.ecb.get_ppi),
            asyncio.to_thread(self.ecb.get_aaa_10y_yield),
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
        ecb_10y  = _safe(ecb_10y)
        snb_cpi  = _safe(snb_cpi)
        snb_core = _safe(snb_core)

        usa_cpi = state.get("inflation")
        usa_ppi = ext.get("ppi")
        usa_core = ext.get("core_cpi")
        usa = InflationDataPoint(
            cpi=usa_cpi,
            core_cpi=usa_core,       # FRED CPILFESL via extended_state
            pce=ext.get("pce"),      # FRED PCEPI via extended_state (Fed-Ziel = PCE)
            ppi=usa_ppi,
            real_rate_10y=ext.get("real_rate_10y"),
            signal=_signal(usa_cpi, core_cpi=usa_core, ppi=usa_ppi, region="usa", real_rate_10y=ext.get("real_rate_10y")),
        )
        # EU Real Rate 10Y = ECB-AAA-10J-Nominalrendite − EU-HICP (Fisher-Näherung)
        eu_real_10y = round(ecb_10y - ecb_cpi, 3) if (ecb_10y is not None and ecb_cpi is not None) else None
        eu = InflationDataPoint(
            cpi=ecb_cpi, core_cpi=ecb_core, pce=None,
            ppi=ecb_ppi, real_rate_10y=eu_real_10y,
            signal=_signal(ecb_cpi, core_cpi=ecb_core, ppi=ecb_ppi, region="eu", real_rate_10y=eu_real_10y),
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
