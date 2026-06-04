import asyncio
from core.domain.events import SectorPerformanceDataReady
from core.domain.models import SectorPerformanceSnapshot
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

USA_SECTORS: dict[str, str] = {
    "Technology":    "XLK",
    "Energy":        "XLE",
    "Financials":    "XLF",
    "Healthcare":    "XLV",
    "Industrials":   "XLI",
    "ConsumerDisc":  "XLY",
    "ConsumerStap":  "XLP",
    "Materials":     "XLB",
    "Utilities":     "XLU",
    "RealEstate":    "XLRE",
}

EU_SECTORS: dict[str, str] = {
    "Technology":    "EXV3.DE",
    "Energy":        "EXH1.DE",
    "Financials":    "EXV1.DE",
    "Healthcare":    "EXV4.DE",
    "Industrials":   "EXH3.DE",
    "ConsumerDisc":  "EXH7.DE",
    "ConsumerStap":  "EXH4.DE",
    "Materials":     "EXV6.DE",
    "Utilities":     "EXH8.DE",
}

_DEFAULT = SectorPerformanceSnapshot(
    usa={}, eurozone={}, leading_usa="n/a", lagging_usa="n/a",
    leading_eu="n/a", lagging_eu="n/a",
)


class SectorPerformanceAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> SectorPerformanceSnapshot:
        usa_prices, eu_prices = await asyncio.gather(
            asyncio.gather(*[
                asyncio.to_thread(self.provider.get_current_price, t)
                for t in USA_SECTORS.values()
            ], return_exceptions=True),
            asyncio.gather(*[
                asyncio.to_thread(self.provider.get_current_price, t)
                for t in EU_SECTORS.values()
            ], return_exceptions=True),
        )

        def _build(names, prices):
            d = {}
            for name, price in zip(names, prices):
                if not isinstance(price, Exception) and price is not None:
                    d[name] = price
            return d

        usa_perf = _build(USA_SECTORS.keys(), usa_prices)
        eu_perf  = _build(EU_SECTORS.keys(), eu_prices)

        leading_usa = max(usa_perf, key=usa_perf.get) if usa_perf else "n/a"
        lagging_usa = min(usa_perf, key=usa_perf.get) if usa_perf else "n/a"
        leading_eu  = max(eu_perf,  key=eu_perf.get)  if eu_perf  else "n/a"
        lagging_eu  = min(eu_perf,  key=eu_perf.get)  if eu_perf  else "n/a"

        result = SectorPerformanceSnapshot(
            usa=usa_perf, eurozone=eu_perf,
            leading_usa=leading_usa, lagging_usa=lagging_usa,
            leading_eu=leading_eu,   lagging_eu=lagging_eu,
        )
        self.bus.publish(SectorPerformanceDataReady(source="sector_performance_agent", payload={
            "leading_usa": leading_usa, "leading_eu": leading_eu,
        }))
        return result

    @staticmethod
    def default() -> SectorPerformanceSnapshot:
        return _DEFAULT
