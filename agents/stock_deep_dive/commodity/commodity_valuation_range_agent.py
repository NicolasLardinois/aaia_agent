import asyncio

from core.domain.events import CommodityValuationRangeReady
from core.domain.models import CommodityValuationRangeSnapshot, Signal, SignalStatus
from core.ports.data_provider import CommoditySupplyProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.relative import percentile_rank

_DEFAULT = CommodityValuationRangeSnapshot(
    current_price=None, price_low_5y=None, price_high_5y=None,
    percentile_5y=None, percentile_10y=None,
    production_cost_low=None, production_cost_high=None,
    position="fair", signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)


def _position(pct: float) -> tuple[str, Signal]:
    if pct < 20:
        return "cheap", Signal.BULLISH
    if pct > 80:
        return "expensive", Signal.BEARISH
    return "fair", Signal.NEUTRAL


def _percentile_of(close: "object") -> tuple[float, float, float, float]:
    current = float(close.iloc[-1])
    hist = [float(x) for x in close.iloc[:-1]]
    pct = percentile_rank(current, hist, winsorize=0.05)
    return current, pct, round(float(close.min()), 2), round(float(close.max()), 2)


class CommodityValuationRangeAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus,
                 supply: CommoditySupplyProvider | None = None):
        self.market = market
        self.bus = bus
        self.supply = supply

    async def run(self, ticker: str) -> CommodityValuationRangeSnapshot:
        hist5y, hist10y = await asyncio.gather(
            asyncio.to_thread(self.market.get_price_history, ticker, "5y"),
            asyncio.to_thread(self.market.get_price_history, ticker, "10y"),
            return_exceptions=True,
        )
        if isinstance(hist5y, Exception) or hist5y is None or "Close" not in getattr(hist5y, "columns", []):
            return _DEFAULT

        close5 = hist5y["Close"].dropna()
        # Nominale Preise. Reale CPI-Deflation ist als Folge-Task ausgelagert (benötigt eine an die
        # Preisdaten ausgerichtete CPI-Index-Serie). Der P4.3-Kernfix ist das echte Rang-Perzentil unten.
        current, pct5y, low5y, high5y = _percentile_of(close5)

        pct10y = None
        if not isinstance(hist10y, Exception) and hist10y is not None and "Close" in getattr(hist10y, "columns", []):
            close10 = hist10y["Close"].dropna()  # nominal; reale Deflation = Folge-Task
            _, pct10y, _, _ = _percentile_of(close10)

        cost_low = cost_high = None
        if self.supply is not None:
            curve = await asyncio.to_thread(self.supply.get_production_cost_curve, ticker)
            if curve:
                cost_low = curve.get("cost_p25")
                cost_high = curve.get("cost_p90")

        pos, sig = _position(pct5y)
        result = CommodityValuationRangeSnapshot(
            current_price=round(current, 2),
            price_low_5y=low5y, price_high_5y=high5y,
            percentile_5y=round(pct5y, 1), percentile_10y=round(pct10y, 1) if pct10y is not None else None,
            production_cost_low=cost_low, production_cost_high=cost_high,
            position=pos, signal=sig, status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(CommodityValuationRangeReady(
            source="commodity_valuation_range_agent", payload={"ticker": ticker},
        ))
        return result

    @staticmethod
    def default() -> CommodityValuationRangeSnapshot:
        return _DEFAULT
