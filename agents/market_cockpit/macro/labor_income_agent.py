import asyncio

from core.domain.events import LaborIncomeReady
from core.domain.models import LaborIncomeSnapshot, LaborIncomeDataPoint, Signal
from core.ports.data_provider import MacroDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = LaborIncomeDataPoint(nominal_wage_growth=None, real_wage_growth=None, signal=Signal.NEUTRAL)
_DEFAULT = LaborIncomeSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(real_wage_growth: float | None) -> Signal:
    if real_wage_growth is None:
        return Signal.NEUTRAL
    if real_wage_growth > 1.0:
        return Signal.BULLISH
    if real_wage_growth < -1.0:
        return Signal.BEARISH
    return Signal.NEUTRAL


class LaborIncomeAgent:
    def __init__(self, provider: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self) -> LaborIncomeSnapshot:
        data = await asyncio.to_thread(self.provider.get_extended_state)

        usa = LaborIncomeDataPoint(
            nominal_wage_growth=data.get("nominal_wage_growth"),
            real_wage_growth=data.get("real_wage_growth"),
            signal=_signal(data.get("real_wage_growth")),
        )
        # TODO: Eurostat / ECB API für EU-Löhne
        # TODO: SNB API für CH-Löhne
        result = LaborIncomeSnapshot(usa=usa, eurozone=_NEUTRAL, switzerland=_NEUTRAL)
        self.bus.publish(LaborIncomeReady(source="labor_income_agent", payload={
            "usa_nominal": usa.nominal_wage_growth,
            "usa_real": usa.real_wage_growth,
        }))
        return result

    @staticmethod
    def default() -> LaborIncomeSnapshot:
        return _DEFAULT
