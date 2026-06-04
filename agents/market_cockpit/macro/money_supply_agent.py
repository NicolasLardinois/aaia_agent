import asyncio
from core.domain.events import MoneySupplyDataReady
from core.domain.models import MoneySupplySnapshot, MoneySupplyDataPoint, Signal
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = MoneySupplyDataPoint(m2_growth=None, m3_growth=None, velocity_m2=None, signal=Signal.NEUTRAL)
_DEFAULT = MoneySupplySnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(m2: float | None, m3: float | None) -> Signal:
    growth = m3 if m3 is not None else m2
    if growth is None:
        return Signal.NEUTRAL
    if 3.0 <= growth <= 8.0:
        return Signal.BULLISH
    if growth > 10.0 or growth < 0.0:
        return Signal.BEARISH
    return Signal.NEUTRAL


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

        usa = MoneySupplyDataPoint(
            m2_growth=usa_m2, m3_growth=None,  # USA publiziert kein M3
            velocity_m2=usa_v,
            signal=_signal(usa_m2, None),
        )
        eu = MoneySupplyDataPoint(
            m2_growth=ecb_m2, m3_growth=ecb_m3, velocity_m2=None,
            signal=_signal(ecb_m2, ecb_m3),
        )
        ch = MoneySupplyDataPoint(
            m2_growth=snb_m2, m3_growth=snb_m3, velocity_m2=None,
            signal=_signal(snb_m2, snb_m3),
        )
        result = MoneySupplySnapshot(usa=usa, eurozone=eu, switzerland=ch)
        self.bus.publish(MoneySupplyDataReady(source="money_supply_agent", payload={
            "usa_m2": usa_m2, "eu_m3": ecb_m3, "ch_m3": snb_m3,
        }))
        return result

    @staticmethod
    def default() -> MoneySupplySnapshot:
        return _DEFAULT
