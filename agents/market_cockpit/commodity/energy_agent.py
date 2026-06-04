import asyncio
from core.domain.events import EnergyDataReady
from core.domain.models import EnergySnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

TICKERS = {"wti": "CL=F", "brent": "BZ=F", "natural_gas": "NG=F"}
_DEFAULT = EnergySnapshot(wti_usd=None, brent_usd=None, natural_gas_usd=None, signal=Signal.NEUTRAL)


def _signal(wti: float | None, brent: float | None) -> Signal:
    price = wti or brent
    if price is None:
        return Signal.NEUTRAL
    # Stark steigende Ölpreise = Inflationsdruck → BEARISH für Konsum
    # Stark fallende Ölpreise = Nachfrageschwäche → auch BEARISH
    # Moderate Preise = NEUTRAL
    if price > 100:
        return Signal.BEARISH
    if price < 40:
        return Signal.BEARISH
    return Signal.NEUTRAL


class EnergyAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> EnergySnapshot:
        wti, brent, gas = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, TICKERS["wti"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["brent"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["natural_gas"]),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        wti = _safe(wti); brent = _safe(brent); gas = _safe(gas)

        result = EnergySnapshot(
            wti_usd=wti, brent_usd=brent, natural_gas_usd=gas,
            signal=_signal(wti, brent),
        )
        self.bus.publish(EnergyDataReady(source="energy_agent", payload={
            "wti": wti, "brent": brent, "natural_gas": gas,
        }))
        return result

    @staticmethod
    def default() -> EnergySnapshot:
        return _DEFAULT
