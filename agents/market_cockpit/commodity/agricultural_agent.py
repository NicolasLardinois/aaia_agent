import asyncio
from core.domain.events import AgriculturalDataReady
from core.domain.models import AgriculturalSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

TICKERS = {
    "wheat":        "ZW=F",
    "corn":         "ZC=F",
    "soy":          "ZS=F",
    "coffee":       "KC=F",
    "sugar":        "SB=F",
    "cotton":       "CT=F",
    "orange_juice": "OJ=F",
}
_DEFAULT = AgriculturalSnapshot(
    wheat_usd=None, corn_usd=None, soy_usd=None, coffee_usd=None,
    sugar_usd=None, cotton_usd=None, orange_juice_usd=None, signal=Signal.NEUTRAL,
)


def _signal(wheat: float | None, corn: float | None) -> Signal:
    # Stark steigende Agrarpreise = Nahrungsmittelinflation → BEARISH für Konsum
    if wheat is None and corn is None:
        return Signal.NEUTRAL
    # TODO: Trendanalyse implementieren wenn Historiedaten verfügbar
    return Signal.NEUTRAL


class AgriculturalAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> AgriculturalSnapshot:
        wheat, corn, soy, coffee, sugar, cotton, oj = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, TICKERS["wheat"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["corn"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["soy"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["coffee"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["sugar"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["cotton"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["orange_juice"]),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        wheat = _safe(wheat); corn = _safe(corn); soy = _safe(soy)
        coffee = _safe(coffee); sugar = _safe(sugar); cotton = _safe(cotton); oj = _safe(oj)

        result = AgriculturalSnapshot(
            wheat_usd=wheat, corn_usd=corn, soy_usd=soy, coffee_usd=coffee,
            sugar_usd=sugar, cotton_usd=cotton, orange_juice_usd=oj,
            signal=_signal(wheat, corn),
        )
        self.bus.publish(AgriculturalDataReady(source="agricultural_agent", payload={
            "wheat": wheat, "corn": corn, "soy": soy,
        }))
        return result

    @staticmethod
    def default() -> AgriculturalSnapshot:
        return _DEFAULT
