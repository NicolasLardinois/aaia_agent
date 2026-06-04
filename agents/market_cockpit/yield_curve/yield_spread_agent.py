import asyncio
from core.domain.events import YieldSpreadDataReady
from core.domain.models import YieldSpreadSnapshot, YieldSpreadDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL_PT = YieldSpreadDataPoint(
    spread_10y2y=None, spread_10y3m=None, spread_30y10y=None,
    inverted=False, signal=Signal.NEUTRAL,
)
_DEFAULT = YieldSpreadSnapshot(usa=_NEUTRAL_PT, eurozone=_NEUTRAL_PT, switzerland=_NEUTRAL_PT)


def _point(s10y2y: float | None, s10y3m: float | None, s30y10y: float | None) -> YieldSpreadDataPoint:
    inverted = (s10y2y is not None and s10y2y < 0) or (s10y3m is not None and s10y3m < 0)
    ref = s10y2y if s10y2y is not None else s10y3m
    if ref is None:
        sig = Signal.NEUTRAL
    elif ref < 0:
        sig = Signal.BEARISH
    elif ref > 1.0:
        sig = Signal.BULLISH
    else:
        sig = Signal.NEUTRAL
    return YieldSpreadDataPoint(
        spread_10y2y=s10y2y, spread_10y3m=s10y3m, spread_30y10y=s30y10y,
        inverted=inverted, signal=sig,
    )


class YieldSpreadAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> YieldSpreadSnapshot:
        state, ext, snb_10y, snb_2y = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.snb.get_sovereign_yield_10y),
            asyncio.to_thread(self.snb.get_sovereign_yield_2y),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        state  = _safe(state)  or {}
        ext    = _safe(ext)    or {}
        snb_10y = _safe(snb_10y)
        snb_2y  = _safe(snb_2y)

        # USA
        usa_10y2y = state.get("yield_curve")      # T10Y2Y
        usa_10y3m = ext.get("yield_curve_3m10y")  # T10Y3M
        usa = _point(usa_10y2y, usa_10y3m, None)

        # EU — TODO: ECB Bund yields
        eu = _point(None, None, None)

        # CH
        ch_spread = round(snb_10y - snb_2y, 3) if snb_10y and snb_2y else None
        ch = _point(ch_spread, None, None)

        result = YieldSpreadSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(YieldSpreadDataReady(source="yield_spread_agent", payload={
            "usa_10y2y": usa_10y2y, "usa_10y3m": usa_10y3m,
        }))
        return result

    @staticmethod
    def default() -> YieldSpreadSnapshot:
        return _DEFAULT
