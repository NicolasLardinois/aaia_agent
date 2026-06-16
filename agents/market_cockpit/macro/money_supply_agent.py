import asyncio
from core.domain.events import MoneySupplyDataReady
from core.domain.models import MoneySupplySnapshot, MoneySupplyDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus
from core.utils.real_nominal import excess_over_nominal_gdp

_NEUTRAL = MoneySupplyDataPoint(m2_growth=None, m3_growth=None, velocity_m2=None, signal=Signal.NEUTRAL)
_DEFAULT = MoneySupplySnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(excess_liquidity: float | None, velocity_trend: str | None) -> Signal:
    """
    Glockenförmig über die ÜBERSCHUSS-LIQUIDITÄT (M-Wachstum − nominales BIP-Wachstum),
    lückenlos: moderater Überschuss (0–4pp) = gesund → BULLISH; exzessiv (>4pp) oder
    Kontraktion (<0) → BEARISH. Sinkende Velocity (MV=PQ) dämpft die Inflationswirkung
    hohen Wachstums → entschärft die obere Flanke.
    """
    if excess_liquidity is None:
        return Signal.NEUTRAL
    if 0.0 <= excess_liquidity <= 4.0:
        sig = Signal.BULLISH
    else:
        sig = Signal.BEARISH   # >4 (Blasenrisiko) ODER <0 (Kontraktion) — keine Lücke
    if sig == Signal.BEARISH and excess_liquidity > 4.0 and velocity_trend == "falling":
        sig = Signal.NEUTRAL   # hohe Geldmenge ohne Umlauf → keine Inflationswirkung
    return sig


class MoneySupplyAgent:
    def __init__(self, macro: MacroDataProvider, ecb: EcbDataProvider, snb: SnbDataProvider, bus: EventBus):
        self.macro = macro
        self.ecb   = ecb
        self.snb   = snb
        self.bus   = bus

    async def run(self) -> MoneySupplySnapshot:
        ext, ecb_m2, ecb_m3, snb_m2, snb_m3 = await asyncio.gather(
            asyncio.to_thread(self.macro.get_extended_state),
            asyncio.to_thread(self.ecb.get_m2_growth),
            asyncio.to_thread(self.ecb.get_m3_growth),
            asyncio.to_thread(self.snb.get_m2_growth),
            asyncio.to_thread(self.snb.get_m3_growth),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v

        ext    = _safe(ext)    or {}
        ecb_m2 = _safe(ecb_m2)
        ecb_m3 = _safe(ecb_m3)
        snb_m2 = _safe(snb_m2)
        snb_m3 = _safe(snb_m3)

        usa_m2 = ext.get("m2_growth")
        usa_v  = ext.get("money_velocity")
        # Nominales BIP-Wachstum = reales BIP + CPI (Proxy)
        usa_gdp  = ext.get("gdp_growth")
        usa_cpi  = ext.get("inflation")
        usa_nom_gdp = (usa_gdp + usa_cpi) if (usa_gdp is not None and usa_cpi is not None) else None
        usa_excess = excess_over_nominal_gdp(usa_m2, usa_nom_gdp) if usa_m2 is not None else None

        usa = MoneySupplyDataPoint(
            m2_growth=usa_m2, m3_growth=None,  # USA publiziert kein M3
            velocity_m2=usa_v,
            signal=_signal(usa_excess, None),
        )
        eu_m = ecb_m3 if ecb_m3 is not None else ecb_m2
        eu_excess = excess_over_nominal_gdp(eu_m, None) if eu_m is not None else None
        eu = MoneySupplyDataPoint(
            m2_growth=ecb_m2, m3_growth=ecb_m3, velocity_m2=None,
            signal=_signal(eu_excess, None),
        )
        ch_m = snb_m3 if snb_m3 is not None else snb_m2
        ch_excess = excess_over_nominal_gdp(ch_m, None) if ch_m is not None else None
        ch = MoneySupplyDataPoint(
            m2_growth=snb_m2, m3_growth=snb_m3, velocity_m2=None,
            signal=_signal(ch_excess, None),
        )
        result = MoneySupplySnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(MoneySupplyDataReady(source="money_supply_agent", payload={
            "usa_m2": usa_m2, "eu_m3": ecb_m3, "ch_m3": snb_m3,
        }))
        return result

    @staticmethod
    def default() -> MoneySupplySnapshot:
        return _DEFAULT
