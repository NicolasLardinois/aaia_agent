import asyncio

from core.domain.events import PreciousMetalDataReady
from core.domain.models import PreciousMetalSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

METAL_TICKERS = {
    "gold":      "GC=F",
    "silver":    "SI=F",
    "platinum":  "PL=F",
    "palladium": "PA=F",
}

_DEFAULT = PreciousMetalSnapshot(
    metal="unknown", price_usd=None, performance={},
    rsi=None, ma50=None, ma200=None,
    stock_to_flow=None, real_yield_correlation=None,
    signal=Signal.NEUTRAL,
)

# Annähernde S2F-Werte (stabil, jährlich aktualisierbar)
STOCK_TO_FLOW = {
    "gold":      62.0,
    "silver":    22.0,
    "platinum":  0.4,
    "palladium": 0.5,
}


class PreciousMetalPriceAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, metal: str) -> PreciousMetalSnapshot:
        ticker = METAL_TICKERS.get(metal.lower())
        if not ticker:
            return _DEFAULT

        price = await asyncio.to_thread(self.provider.get_current_price, ticker)
        history = await asyncio.to_thread(self.provider.get_price_history, ticker, "5y")

        # TODO: RSI, MA50/200 aus history berechnen wenn Yahoo Finance Adapter bereit
        result = PreciousMetalSnapshot(
            metal=metal,
            price_usd=price,
            performance={},           # TODO: 1W/1M/3M/1Y/5Y aus history
            rsi=None,
            ma50=None,
            ma200=None,
            stock_to_flow=STOCK_TO_FLOW.get(metal.lower()),
            real_yield_correlation=None,  # TODO: Korrelation mit Realzins berechnen
            signal=Signal.NEUTRAL,        # TODO: Signal aus Momentum ableiten
        )
        self.bus.publish(PreciousMetalDataReady(source="precious_metal_price_agent", payload={
            "metal": metal, "price_usd": price,
        }))
        return result

    @staticmethod
    def default(metal: str = "gold") -> PreciousMetalSnapshot:
        return PreciousMetalSnapshot(
            metal=metal, price_usd=None, performance={},
            rsi=None, ma50=None, ma200=None,
            stock_to_flow=STOCK_TO_FLOW.get(metal, None),
            real_yield_correlation=None, signal=Signal.NEUTRAL,
        )
