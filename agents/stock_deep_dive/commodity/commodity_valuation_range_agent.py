import asyncio

from core.domain.events import CommodityValuationRangeReady
from core.domain.models import CommodityValuationRangeSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = CommodityValuationRangeSnapshot(
    current_price=None, price_low_5y=None, price_high_5y=None,
    percentile_5y=None, percentile_10y=None,
    production_cost_low=None, production_cost_high=None,
    position="fair", signal=Signal.NEUTRAL,
)


def _percentile(current: float, low: float, high: float) -> float:
    if high == low:
        return 50.0
    return round((current - low) / (high - low) * 100, 1)


def _position(pct: float) -> tuple[str, Signal]:
    if pct < 20:
        return "cheap", Signal.BULLISH
    if pct > 80:
        return "expensive", Signal.BEARISH
    return "fair", Signal.NEUTRAL


class CommodityValuationRangeAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> CommodityValuationRangeSnapshot:
        try:
            hist5y, hist10y = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, "5y"),
                asyncio.to_thread(self.market.get_price_history, ticker, "10y"),
                return_exceptions=True,
            )
            if isinstance(hist5y, Exception):
                return _DEFAULT

            close5  = hist5y["Close"]
            current = float(close5.iloc[-1])
            low5y   = round(float(close5.min()), 2)
            high5y  = round(float(close5.max()), 2)
            pct5y   = _percentile(current, low5y, high5y)

            pct10y = None
            if not isinstance(hist10y, Exception):
                close10 = hist10y["Close"]
                pct10y  = _percentile(current, float(close10.min()), float(close10.max()))

            pos, sig = _position(pct5y)

            result = CommodityValuationRangeSnapshot(
                current_price=round(current, 2),
                price_low_5y=low5y,
                price_high_5y=high5y,
                percentile_5y=pct5y,
                percentile_10y=pct10y,
                production_cost_low=None,    # TODO: commodity-spezifische Kostenmodelle
                production_cost_high=None,
                position=pos,
                signal=sig,
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(CommodityValuationRangeReady(
            source="commodity_valuation_range_agent", payload={"ticker": ticker},
        ))
        return result

    @staticmethod
    def default() -> CommodityValuationRangeSnapshot:
        return _DEFAULT
