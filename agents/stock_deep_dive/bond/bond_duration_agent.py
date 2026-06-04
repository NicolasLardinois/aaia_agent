import asyncio
from core.domain.events import BondDurationReady
from core.domain.models import BondDurationSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = BondDurationSnapshot(
    macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL,
)


def _signal(mod_duration: float | None, rate_direction: str = "stable") -> Signal:
    if mod_duration is None:
        return Signal.NEUTRAL
    # Hohe Duration bei steigenden Zinsen = Kursverlustrisiko → BEARISH
    if mod_duration > 10 and rate_direction == "rising":
        return Signal.BEARISH
    # Hohe Duration bei sinkenden Zinsen = Kursgewinnpotenzial → BULLISH
    if mod_duration > 10 and rate_direction == "falling":
        return Signal.BULLISH
    return Signal.NEUTRAL


class BondDurationAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self, ticker: str, rate_direction: str = "stable") -> BondDurationSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        mac_dur = data.get("macaulay_duration")
        mod_dur = data.get("modified_duration")
        convex  = data.get("convexity")
        # DV01: Kurswertänderung bei 1 Basispunkt = modified_duration * price * 0.0001
        price   = data.get("current_price")
        dv01    = round(mod_dur * price * 0.0001, 4) if mod_dur and price else None

        result = BondDurationSnapshot(
            macaulay_duration=mac_dur, modified_duration=mod_dur,
            convexity=convex, dv01=dv01,
            signal=_signal(mod_dur, rate_direction),
        )
        self.bus.publish(BondDurationReady(source="bond_duration_agent", payload={
            "ticker": ticker, "modified_duration": mod_dur,
        }))
        return result

    @staticmethod
    def default() -> BondDurationSnapshot:
        return _DEFAULT
