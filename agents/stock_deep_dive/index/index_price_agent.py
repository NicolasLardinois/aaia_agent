import asyncio
from datetime import datetime

from core.domain.events import IndexPriceReady
from core.domain.models import IndexPriceSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexPriceSnapshot(
    current_price=None, perf_1w=None, perf_1m=None, perf_3m=None,
    perf_ytd=None, perf_1y=None, perf_3y=None, perf_5y=None,
    high_52w=None, low_52w=None, signal=Signal.NEUTRAL,
)


def _pct(new, old) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 2)


def _signal(perf_1y: float | None, perf_3m: float | None) -> Signal:
    if perf_1y is None:
        return Signal.NEUTRAL
    if perf_1y > 15 and (perf_3m is None or perf_3m > 0):
        return Signal.BULLISH
    if perf_1y < -15:
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexPriceAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexPriceSnapshot:
        try:
            hist, info = await asyncio.gather(
                asyncio.to_thread(self.market.get_price_history, ticker, "5y"),
                asyncio.to_thread(self.market.get_info, ticker),
                return_exceptions=True,
            )
            if isinstance(hist, Exception) or isinstance(info, Exception):
                return _DEFAULT

            close = hist["Close"]
            now   = close.iloc[-1]

            def _ago(days):
                idx = close.index.searchsorted(close.index[-1] - __import__("pandas").Timedelta(days=days))
                return close.iloc[max(0, idx - 1)] if idx > 0 else None

            p1w   = _pct(now, _ago(7))
            p1m   = _pct(now, _ago(30))
            p3m   = _pct(now, _ago(90))
            p1y   = _pct(now, _ago(365))
            p3y   = _pct(now, _ago(365 * 3))
            p5y   = _pct(now, _ago(365 * 5))

            ytd_start_idx = close.index.searchsorted(f"{datetime.utcnow().year}-01-01")
            ytd_price     = close.iloc[ytd_start_idx] if ytd_start_idx < len(close) else None
            p_ytd = _pct(now, ytd_price)

            result = IndexPriceSnapshot(
                current_price=round(float(now), 2),
                perf_1w=p1w, perf_1m=p1m, perf_3m=p3m, perf_ytd=p_ytd,
                perf_1y=p1y, perf_3y=p3y, perf_5y=p5y,
                high_52w=info.get("fiftyTwoWeekHigh"),
                low_52w=info.get("fiftyTwoWeekLow"),
                signal=_signal(p1y, p3m),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexPriceSnapshot:
        return _DEFAULT
