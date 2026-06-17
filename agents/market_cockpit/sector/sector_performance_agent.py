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
    "CommServices":  "XLC",
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

_USA_BENCHMARK = "SPY"
_EU_BENCHMARK  = "EXW1.DE"   # iShares STOXX Europe 600


def _relative_strength(perf: dict[str, float], benchmark_return: float | None) -> dict[str, float]:
    """Relative Stärke = Sektor-Return − Benchmark-Return (entfernt das Markt-Beta-Artefakt)."""
    if benchmark_return is None:
        return dict(perf)
    return {name: round(ret - benchmark_return, 2) for name, ret in perf.items()}


class SectorPerformanceAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> SectorPerformanceSnapshot:
        usa_hists, eu_hists, (spy_hist, eu_bench_hist) = await asyncio.gather(
            asyncio.gather(*[
                asyncio.to_thread(self.provider.get_price_history, t, "1mo")
                for t in USA_SECTORS.values()
            ], return_exceptions=True),
            asyncio.gather(*[
                asyncio.to_thread(self.provider.get_price_history, t, "1mo")
                for t in EU_SECTORS.values()
            ], return_exceptions=True),
            asyncio.gather(
                asyncio.to_thread(self.provider.get_price_history, _USA_BENCHMARK, "1mo"),
                asyncio.to_thread(self.provider.get_price_history, _EU_BENCHMARK, "1mo"),
                return_exceptions=True,
            ),
        )

        def _pct_return(hist) -> float | None:
            if isinstance(hist, Exception) or hist is None:
                return None
            try:
                if len(hist) < 2:
                    return None
                first = hist["Close"].iloc[0]
                last  = hist["Close"].iloc[-1]
                if first <= 0:
                    return None
                return round(float((last - first) / first * 100), 2)
            except Exception:
                return None

        def _build(names, hists):
            d = {}
            for name, hist in zip(names, hists):
                ret = _pct_return(hist)
                if ret is not None:
                    d[name] = ret
            return d

        usa_perf = _build(USA_SECTORS.keys(), usa_hists)
        eu_perf  = _build(EU_SECTORS.keys(), eu_hists)

        spy_return    = _pct_return(spy_hist)
        eu_bench_return = _pct_return(eu_bench_hist)

        usa_rs = _relative_strength(usa_perf, spy_return)
        eu_rs  = _relative_strength(eu_perf,  eu_bench_return)

        leading_usa = max(usa_rs, key=usa_rs.get) if usa_rs else "n/a"
        lagging_usa = min(usa_rs, key=usa_rs.get) if usa_rs else "n/a"
        leading_eu  = max(eu_rs,  key=eu_rs.get)  if eu_rs  else "n/a"
        lagging_eu  = min(eu_rs,  key=eu_rs.get)  if eu_rs  else "n/a"

        result = SectorPerformanceSnapshot(
            usa=usa_rs, eurozone=eu_rs,
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
