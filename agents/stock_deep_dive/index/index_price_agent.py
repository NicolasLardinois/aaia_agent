import asyncio
from datetime import datetime, timezone

import pandas as pd

from core.domain.events import IndexPriceReady
from core.domain.models import IndexPriceSnapshot, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexPriceSnapshot(
    current_price=None, perf_1w=None, perf_1m=None, perf_3m=None, perf_ytd=None,
    perf_1y=None, perf_3y=None, perf_5y=None, high_52w=None, low_52w=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)


def _pct(new, old) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 2)


def _52w(close: "object") -> tuple[float | None, float | None]:
    window = close.iloc[-252:] if len(close) >= 252 else close
    return round(float(window.max()), 2), round(float(window.min()), 2)


def _signal(perf_1y: float | None, perf_3m: float | None, dist_52w_high: float | None) -> Signal:
    if perf_1y is None:
        return Signal.NEUTRAL
    near_high = dist_52w_high is None or dist_52w_high > -5.0
    if perf_1y > 15 and (perf_3m is None or perf_3m > 0) and near_high:
        return Signal.BULLISH
    if perf_1y < -15:
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexPriceAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus = bus

    async def run(self, ticker: str) -> IndexPriceSnapshot:
        # Kursrendite (Price Return, ohne Dividenden) — bewusste Wahl: annahmefrei und
        # passend zur Schweizer Sicht (steuerfreier Kapitalgewinn; Dividenden separat steuerpflichtig).
        hist = await asyncio.to_thread(self.market.get_price_history, ticker, "5y")
        if hist is None or "Close" not in getattr(hist, "columns", []):
            self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
            return _DEFAULT

        close = hist["Close"].dropna()
        if close.empty:
            self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
            return _DEFAULT
        now = float(close.iloc[-1])

        def _ago(days):
            idx = close.index.searchsorted(close.index[-1] - pd.Timedelta(days=days))
            return float(close.iloc[max(0, idx - 1)]) if idx > 0 else None

        high_52w, low_52w = _52w(close)
        dist_high = _pct(now, high_52w)
        p3m, p1y = _pct(now, _ago(90)), _pct(now, _ago(365))

        ytd_idx = close.index.searchsorted(f"{datetime.now(timezone.utc).year}-01-01")
        ytd_price = float(close.iloc[ytd_idx]) if ytd_idx < len(close) else None

        result = IndexPriceSnapshot(
            current_price=round(now, 2),
            perf_1w=_pct(now, _ago(7)), perf_1m=_pct(now, _ago(30)), perf_3m=p3m,
            perf_ytd=_pct(now, ytd_price), perf_1y=p1y,
            perf_3y=_pct(now, _ago(365 * 3)), perf_5y=_pct(now, _ago(365 * 5)),
            high_52w=high_52w, low_52w=low_52w,
            signal=_signal(p1y, p3m, dist_high), status=SignalStatus.AVAILABLE,
        )
        self.bus.publish(IndexPriceReady(source="index_price_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexPriceSnapshot:
        return _DEFAULT
