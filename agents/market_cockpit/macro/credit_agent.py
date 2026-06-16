import asyncio

from core.domain.events import CreditDataReady
from core.domain.models import CreditSnapshot, CreditDataPoint, Signal
from core.ports.data_provider import MacroDataProvider
from core.ports.event_bus import EventBus
from core.utils.real_nominal import to_real

_NEUTRAL = CreditDataPoint(credit_growth=None, money_velocity=None, signal=Signal.NEUTRAL)
_DEFAULT = CreditSnapshot(usa=_NEUTRAL, eurozone=_NEUTRAL, switzerland=_NEUTRAL)


def _signal(real_credit_growth: float | None) -> Signal:
    """
    Glockenförmig über das REALE Kreditwachstum (nominal − CPI): moderate
    Expansion (2–12%) = Liquidität → BULLISH; exzessiv (>12%) = Kreditboom /
    Krisen-Frühwarnung (BIS Credit-Gap) → BEARISH; Kontraktion (<0) → BEARISH;
    schwach (0–2%) → NEUTRAL.
    Hinweis: money_velocity fließt nicht ins Signal (Doppelung mit money_supply
    vermieden) — das Feld bleibt im Snapshot für Dashboard-Zwecke erhalten.
    """
    if real_credit_growth is None:
        return Signal.NEUTRAL
    if real_credit_growth < 0.0:
        return Signal.BEARISH
    if real_credit_growth < 2.0:
        return Signal.NEUTRAL
    if real_credit_growth <= 12.0:
        return Signal.BULLISH
    return Signal.BEARISH


class CreditAgent:
    def __init__(self, provider: MacroDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self) -> CreditSnapshot:
        try:
            data = await asyncio.to_thread(self.provider.get_extended_state)
        except Exception:
            return _DEFAULT

        nominal_credit = data.get("credit_growth")
        cpi = data.get("inflation")
        # Reales Kreditwachstum = nominal − CPI (Fisher-Bereinigung via to_real)
        real_credit = None
        if nominal_credit is not None and cpi is not None:
            try:
                real_credit = to_real(nominal_credit, cpi)
            except Exception:
                real_credit = None
        elif nominal_credit is not None:
            # Fallback: kein CPI verfügbar → nominales Wachstum (dokumentiert)
            real_credit = nominal_credit

        usa = CreditDataPoint(
            credit_growth=nominal_credit,
            money_velocity=data.get("money_velocity"),
            signal=_signal(real_credit),
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
