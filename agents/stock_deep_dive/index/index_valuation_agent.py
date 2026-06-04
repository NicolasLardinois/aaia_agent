import asyncio

from core.domain.events import IndexValuationReady
from core.domain.models import IndexValuationSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = IndexValuationSnapshot(
    pe_trailing=None, pe_forward=None, shiller_cape=None,
    dividend_yield=None, ev_ebitda=None, signal=Signal.NEUTRAL,
)

# Historical P/E fair-value ranges per index (low, high)
_PE_RANGES: dict[str, tuple[float, float]] = {
    "^GSPC":    (15.0, 25.0),
    "^NDX":     (20.0, 35.0),
    "^DJI":     (15.0, 23.0),
    "^RUT":     (18.0, 32.0),
    "^STOXX50E":(12.0, 20.0),
    "^GDAXI":   (12.0, 18.0),
    "^FCHI":    (13.0, 20.0),
    "^SSMI":    (16.0, 24.0),
    "^N225":    (14.0, 22.0),
    "^HSI":     (10.0, 16.0),
}
_DEFAULT_PE_RANGE = (15.0, 25.0)


def _signal(pe: float | None, ticker: str) -> Signal:
    if pe is None:
        return Signal.NEUTRAL
    lo, hi = _PE_RANGES.get(ticker, _DEFAULT_PE_RANGE)
    if pe < lo * 0.85:
        return Signal.BULLISH
    if pe > hi * 1.20:
        return Signal.BEARISH
    return Signal.NEUTRAL


class IndexValuationAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> IndexValuationSnapshot:
        try:
            info = await asyncio.to_thread(self.market.get_info, ticker)
            if isinstance(info, Exception) or not info:
                return _DEFAULT

            pe       = info.get("trailingPE")
            fwd_pe   = info.get("forwardPE")
            div_y    = info.get("dividendYield")
            ev_ebitda = info.get("enterpriseToEbitda")

            result = IndexValuationSnapshot(
                pe_trailing=round(pe, 2) if pe else None,
                pe_forward=round(fwd_pe, 2) if fwd_pe else None,
                shiller_cape=None,   # TODO: Quandl / multpl.com
                dividend_yield=round(div_y * 100, 2) if div_y else None,
                ev_ebitda=round(ev_ebitda, 2) if ev_ebitda else None,
                signal=_signal(pe, ticker),
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexValuationReady(source="index_valuation_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexValuationSnapshot:
        return _DEFAULT
