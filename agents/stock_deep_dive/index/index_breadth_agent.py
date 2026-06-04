import asyncio

from core.domain.events import IndexBreadthReady
from core.domain.models import IndexBreadthSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexBreadthSnapshot(
    pct_above_ma50=None, pct_above_ma200=None,
    advance_decline_ratio=None, new_highs=None, new_lows=None,
    signal=Signal.NEUTRAL,
)

# TODO: Echte Breadth-Daten erfordern Preisdaten aller Komponenten.
# Quellen: FRED (SPSICOMP), StockCharts, Bloomberg Terminal.
# Aktuell Stub — wird implementiert wenn Datenquelle verfügbar.


def _signal(pct_ma200: float | None) -> Signal:
    if pct_ma200 is None:
        return Signal.NEUTRAL
    if pct_ma200 > 70:
        return Signal.BULLISH
    if pct_ma200 < 30:
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexBreadthAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexBreadthSnapshot:
        self.bus.publish(IndexBreadthReady(source="index_breadth_agent", payload={"ticker": ticker}))
        return _DEFAULT

    @staticmethod
    def default() -> IndexBreadthSnapshot:
        return _DEFAULT
