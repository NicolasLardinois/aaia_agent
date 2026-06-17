import asyncio
from core.domain.events import VIXDataReady
from core.domain.models import VIXSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = VIXSnapshot(vix=None, vstoxx=None, signal=Signal.NEUTRAL)


def _signal(vix: float | None, vstoxx: float | None) -> Signal:
    """
    Contrarian (konsistent mit Fear&Greed/Put-Call): VIX-Spike (>30) = Panik
    = Kaufgelegenheit → BULLISH; sehr niedriger VIX (<15) = Sorglosigkeit → BEARISH.
    `is None`-Check statt Falsiness (vix=0.0 ist gültig).
    """
    ref = vix if vix is not None else vstoxx
    if ref is None:
        return Signal.NEUTRAL
    if ref > 30:
        return Signal.BULLISH
    if ref < 15:
        return Signal.BEARISH
    return Signal.NEUTRAL


class VIXAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> VIXSnapshot:
        vix, vstoxx = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, "^VIX"),
            asyncio.to_thread(self.provider.get_current_price, "^V2TX"),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        vix = _safe(vix); vstoxx = _safe(vstoxx)

        result = VIXSnapshot(vix=vix, vstoxx=vstoxx, signal=_signal(vix, vstoxx))
        self.bus.publish(VIXDataReady(source="vix_agent", payload={"vix": vix, "vstoxx": vstoxx}))
        return result

    @staticmethod
    def default() -> VIXSnapshot:
        return _DEFAULT
