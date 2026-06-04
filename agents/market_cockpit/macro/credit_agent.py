import asyncio

from core.domain.events import CreditDataReady
from core.domain.models import CreditSnapshot, CreditDataPoint, Signal
from core.ports.data_provider import MacroDataProvider
from core.ports.event_bus import EventBus

_NEUTRAL = CreditDataPoint(credit_growth=None, money_velocity=None, signal=Signal.NEUTRAL)
_DEFAULT = CreditSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(credit_growth: float | None) -> Signal:
    if credit_growth is None:
        return Signal.NEUTRAL
    if credit_growth > 8.0:
        return Signal.BULLISH   # starkes Kreditwachstum → Expansion
    if credit_growth < 0.0:
        return Signal.BEARISH   # schrumpfendes Kreditvolumen → Kontraktion
    return Signal.NEUTRAL


class CreditAgent:
    def __init__(self, provider: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self) -> CreditSnapshot:
        data = await asyncio.to_thread(self.provider.get_extended_state)

        usa = CreditDataPoint(
            credit_growth=data.get("credit_growth"),
            money_velocity=data.get("money_velocity"),
            signal=_signal(data.get("credit_growth")),
        )
        # TODO: ECB API für EU-Kreditwachstum
        # TODO: SNB API für CH-Kreditwachstum
        result = CreditSnapshot(usa=usa, eurozone=_NEUTRAL, switzerland=_NEUTRAL)
        self.bus.publish(CreditDataReady(source="credit_agent", payload={
            "usa_credit_growth": usa.credit_growth,
            "usa_money_velocity": usa.money_velocity,
        }))
        return result

    @staticmethod
    def default() -> CreditSnapshot:
        return _DEFAULT
