import asyncio

from core.domain.events import IndexBreadthReady
from core.domain.models import IndexBreadthSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexBreadthSnapshot(
    pct_above_ma50=None, pct_above_ma200=None, advance_decline_ratio=None,
    new_highs=None, new_lows=None, signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)


def _signal(pct_above_ma200: float | None) -> Signal:
    if pct_above_ma200 is None:
        return Signal.NEUTRAL
    if pct_above_ma200 > 70:
        return Signal.BULLISH
    if pct_above_ma200 < 30:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _breadth(histories: dict) -> dict:
    above50 = above200 = advancers = decliners = new_high = new_low = total = 0
    for series in histories.values():
        s = series.dropna()
        if len(s) < 200:
            continue
        total += 1
        last = float(s.iloc[-1])
        if last > float(s.rolling(50).mean().iloc[-1]):
            above50 += 1
        if last > float(s.rolling(200).mean().iloc[-1]):
            above200 += 1
        if len(s) >= 2 and last > float(s.iloc[-2]):
            advancers += 1
        elif len(s) >= 2:
            decliners += 1
        window = s.iloc[-252:] if len(s) >= 252 else s
        if last >= float(window.max()):
            new_high += 1
        if last <= float(window.min()):
            new_low += 1
    if total == 0:
        return {}
    return {
        "pct_above_ma50": round(above50 / total * 100, 1),
        "pct_above_ma200": round(above200 / total * 100, 1),
        "advance_decline_ratio": round(advancers / decliners, 2) if decliners else None,
        "new_highs": new_high,
        "new_lows": new_low,
    }


class IndexBreadthAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus = bus

    async def run(self, ticker: str) -> IndexBreadthSnapshot:
        histories = await asyncio.to_thread(self.market.get_constituent_histories, ticker, "2y")
        stats = _breadth(histories) if histories else {}
        if not stats:
            self.bus.publish(IndexBreadthReady(source="index_breadth_agent", payload={"ticker": ticker}))
            return _DEFAULT
        result = IndexBreadthSnapshot(
            pct_above_ma50=stats["pct_above_ma50"],
            pct_above_ma200=stats["pct_above_ma200"],
            advance_decline_ratio=stats["advance_decline_ratio"],
            new_highs=stats["new_highs"], new_lows=stats["new_lows"],
            signal=_signal(stats["pct_above_ma200"]), status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(IndexBreadthReady(source="index_breadth_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexBreadthSnapshot:
        return _DEFAULT
