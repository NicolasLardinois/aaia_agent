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


_STEEP = 1.0   # ref > 1.0 = deutlich positive Kurve


def _point(
    s10y2y: float | None,
    s10y3m: float | None,
    s30y10y: float | None,
    prev_10y3m: float | None = None,
) -> YieldSpreadDataPoint:
    """
    10Y-3M als Primärspread (NY-Fed/Estrella — überlegener Rezessionsprädiktor).
    Inversions-LAG: Eine Inversion ist eine WARNUNG, kein sofortiges BEARISH —
    historisch laufen Aktien 6–18M nach Inversion weiter. Das eigentliche
    Timing-Signal (BEARISH) ist das Bull-Steepening: der Spread bewegt sich aus
    der Inversion heraus nach oben (prev < 0 und current > prev).
    """
    inverted = (s10y3m is not None and s10y3m < 0) or (s10y2y is not None and s10y2y < 0)
    ref = s10y3m if s10y3m is not None else s10y2y
    if ref is None:
        sig = Signal.NEUTRAL
    elif prev_10y3m is not None and prev_10y3m < 0 and ref > prev_10y3m:
        sig = Signal.BEARISH        # Bull-Steepening nach Inversion = Timing-Signal
    elif ref < 0:
        sig = Signal.NEUTRAL        # frische/fortlaufende Inversion = Warnung, kein BEARISH
    elif ref > _STEEP:
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
        state, ext, ecb_spreads, snb_spreads = await asyncio.gather(
            asyncio.to_thread(self.macro.get_economic_state),
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_yield_spreads),
            asyncio.to_thread(self.snb.get_yield_spreads),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        state       = _safe(state)       or {}
        ext         = _safe(ext)         or {}
        ecb_spreads = _safe(ecb_spreads) or {}
        snb_spreads = _safe(snb_spreads) or {}

        # USA — T10Y2Y from economic_state, T10Y3M from extended_state
        usa_10y2y = state.get("yield_curve")
        usa_10y3m = ext.get("yield_curve_3m10y")
        usa = _point(usa_10y2y, usa_10y3m, None)

        # EU — ECB SDW: SR_10Y minus SR_2Y und SR_10Y minus SR_3M
        eu = _point(ecb_spreads.get("10y2y"), ecb_spreads.get("10y3m"), None)

        # CH — FRED OECD: 10y minus 3M SARON (kein 2J CH-Bond frei verfügbar)
        ch = _point(None, snb_spreads.get("10y3m"), None)

        result = YieldSpreadSnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(YieldSpreadDataReady(source="yield_spread_agent", payload={
            "usa_10y2y": usa_10y2y, "usa_10y3m": usa_10y3m,
        }))
        return result

    @staticmethod
    def default() -> YieldSpreadSnapshot:
        return _DEFAULT
