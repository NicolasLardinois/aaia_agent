import asyncio

from core.domain.events import ShortInterestReady
from core.domain.models import ShortInterestSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL)

_HIGH_FLOAT = 20.0       # % des Float → erhöhte Aufmerksamkeit
_HIGH_DTC   = 5.0        # Days-to-Cover → Squeeze-Anfälligkeit


def _signal(short_float: float | None, dtc: float | None, trend: str) -> Signal:
    """Kombiniert Short-%-Float, days_to_cover und Trend.
    - Niedriger Short-Float: NEUTRAL (keine Information).
    - Hoher Short-Float + steigend: BEARISH (bestätigte Skepsis).
    - Hoher Short-Float + fallend + hoher DTC: BULLISH (Squeeze-Brennstoff, sich auflösend).
    - Sonst: NEUTRAL.

    Datenannahme: short_float_trend ('rising'|'stable'|'falling') aus get_short_interest;
    fehlt es → 'stable' (kein Signal).
    """
    if short_float is None:
        return Signal.NEUTRAL
    if short_float < _HIGH_FLOAT:
        return Signal.NEUTRAL

    # Ab hier: hoher Short-Float → kontextabhängig
    if trend == "rising":
        return Signal.BEARISH
    if trend == "falling" and dtc is not None and dtc >= _HIGH_DTC:
        return Signal.BULLISH
    return Signal.NEUTRAL


class ShortInterestAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> ShortInterestSnapshot:
        data = await asyncio.to_thread(self.provider.get_short_interest, ticker)
        short_float = data.get("short_float_pct")
        dtc = data.get("days_to_cover")
        trend = data.get("short_float_trend", "stable")
        result = ShortInterestSnapshot(
            short_float_pct=short_float, days_to_cover=dtc,
            signal=_signal(short_float, dtc, trend),
        )
        self.bus.publish(ShortInterestReady(source="short_interest_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> ShortInterestSnapshot:
        return _DEFAULT
