import asyncio
from core.domain.events import InflationDataReady
from core.domain.models import InflationSnapshot, InflationDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = InflationDataPoint(cpi=None, core_cpi=None, pce=None, ppi=None, real_rate_10y=None, signal=Signal.NEUTRAL)
_DEFAULT = InflationSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(cpi: float | None, trend: str = "stable") -> Signal:
    # trend: "rising" | "falling" | "stable" — für spätere Trendanalyse reserviert
    # (benötigt historische CPI-Daten, noch nicht implementiert)
    if cpi is None:
        return Signal.NEUTRAL
    if cpi < 0.0:
        return Signal.BEARISH   # Deflation
    if cpi < 1.0:
        return Signal.NEUTRAL   # zu tief — Deflationsrisiko
    if cpi <= 3.0:
        return Signal.BULLISH   # Zielbereich
    if cpi >= 4.0:
        return Signal.BEARISH   # klar zu hoch
    return Signal.NEUTRAL       # 3–4%: erhöht aber nicht kritisch


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

        usa = InflationDataPoint(
            cpi=state.get("inflation"),
            core_cpi=None,           # TODO: FRED CPILFESL via extended_state
            pce=None,                # TODO: FRED PCEPI via extended_state
            ppi=ext.get("ppi"),
            real_rate_10y=ext.get("real_rate_10y"),
            signal=_signal(state.get("inflation")),
        )
        eu = InflationDataPoint(
            cpi=ecb_cpi, core_cpi=ecb_core, pce=None,
            ppi=ecb_ppi, real_rate_10y=None,
            signal=_signal(ecb_cpi),
        )
        ch = InflationDataPoint(
            cpi=snb_cpi, core_cpi=snb_core, pce=None,
            ppi=None, real_rate_10y=None,
            signal=_signal(snb_cpi),
        )
        result = InflationSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(InflationDataReady(source="inflation_agent", payload={
            "usa_cpi": usa.cpi, "eu_cpi": ecb_cpi, "ch_cpi": snb_cpi,
        }))
        return result

    @staticmethod
    def default() -> InflationSnapshot:
        return _DEFAULT
