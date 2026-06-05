import asyncio

from core.domain.events import IndexValuationRangeReady
from core.domain.models import IndexValuationRangeSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexValuationRangeSnapshot(
    eps_estimate=None, pe_historical_low=None, pe_historical_high=None,
    price_low=None, price_mid=None, price_high=None,
    current_price=None, position="fair", signal=Signal.NEUTRAL,
)

# Historische P/E-Bandbreiten pro Index (low, mid, high)
_PE_RANGES: dict[str, tuple[float, float, float]] = {
    "^GSPC":     (15.0, 18.0, 25.0),
    "^NDX":      (20.0, 27.0, 35.0),
    "^DJI":      (15.0, 18.0, 23.0),
    "^RUT":      (18.0, 24.0, 32.0),
    "^STOXX50E": (12.0, 15.0, 20.0),
    "^GDAXI":    (12.0, 14.0, 18.0),
    "^FCHI":     (13.0, 16.0, 20.0),
    "^SSMI":     (16.0, 19.0, 24.0),
    "^N225":     (14.0, 17.0, 22.0),
    "^HSI":      (10.0, 12.0, 16.0),
}
_DEFAULT_PE_RANGE = (15.0, 18.0, 25.0)

def _method1_position(current: float, price_low: float, price_high: float) -> tuple[str, int]:
    """Method 1: EPS × historische KGV-Bandbreite."""
    if current < price_low * 0.95:
        return "undervalued", 1
    if current > price_high * 1.05:
        return "overvalued", -1
    return "fair", 0


def _method2_signal(pe_trailing: float | None, pe_mid: float) -> int:
    """Method 2: Aktuelles KGV vs. historischem Durchschnitt."""
    if pe_trailing is None:
        return 0
    if pe_trailing < pe_mid * 0.85:
        return 1    # deutlich günstiger als historischer Schnitt
    if pe_trailing > pe_mid * 1.20:
        return -1   # deutlich teurer als historischer Schnitt
    return 0


def _combine(m1_pts: int, m2_pts: int) -> tuple[str, Signal]:
    total = m1_pts + m2_pts
    if total >= 1:
        return "undervalued", Signal.BULLISH
    if total <= -1:
        return "overvalued", Signal.BEARISH
    return "fair", Signal.NEUTRAL


class IndexValuationRangeAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexValuationRangeSnapshot:
        try:
            info = await asyncio.to_thread(self.market.get_info, ticker)
            if isinstance(info, Exception) or not info:
                return _DEFAULT

            pe_low, pe_mid, pe_high = _PE_RANGES.get(ticker, _DEFAULT_PE_RANGE)

            eps        = info.get("trailingEps") or info.get("forwardEps")
            current    = info.get("regularMarketPrice") or info.get("currentPrice")
            pe_trailing = info.get("trailingPE")

            # Method 1: EPS × historische KGV-Bandbreite
            if eps is not None and eps > 0:
                price_low  = round(eps * pe_low, 2)
                price_mid  = round(eps * pe_mid, 2)
                price_high = round(eps * pe_high, 2)
            else:
                price_low = price_mid = price_high = None

            m1_pts = 0
            if current is not None and price_low is not None and price_high is not None:
                _, m1_pts = _method1_position(current, price_low, price_high)

            # Method 2: Aktuelles KGV vs. historischem Durchschnitt
            m2_pts = _method2_signal(pe_trailing, pe_mid)

            pos, sig = _combine(m1_pts, m2_pts)

            result = IndexValuationRangeSnapshot(
                eps_estimate=round(eps, 2) if eps else None,
                pe_historical_low=pe_low,
                pe_historical_high=pe_high,
                price_low=price_low,
                price_mid=price_mid,
                price_high=price_high,
                current_price=round(current, 2) if current else None,
                position=pos,
                signal=sig,
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexValuationRangeReady(
            source="index_valuation_range_agent", payload={"ticker": ticker},
        ))
        return result

    @staticmethod
    def default() -> IndexValuationRangeSnapshot:
        return _DEFAULT
