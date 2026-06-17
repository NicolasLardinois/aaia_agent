import asyncio

from core.domain.events import IndexValuationReady
from core.domain.models import IndexValuationSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.valuation_math import earnings_yield, equity_risk_premium, shiller_cape

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

# Symmetrischer Puffer um die historische PE-Range (vorher asymmetrisch 0.85/1.20 -> Bullish-Bias).
_PE_BUFFER = 0.10

# ERP-Schwellen (Earnings Yield minus lokaler 10J-Yield): unter 0 teuer, über _ERP_BULLISH günstig.
_ERP_BEARISH = 0.0
_ERP_BULLISH = 0.04


def _signal(pe: float | None, ticker: str) -> Signal:
    if pe is None or pe <= 0:
        return Signal.NEUTRAL
    lo, hi = _PE_RANGES.get(ticker, _DEFAULT_PE_RANGE)
    if pe < lo * (1 - _PE_BUFFER):
        return Signal.BULLISH
    if pe > hi * (1 + _PE_BUFFER):
        return Signal.BEARISH
    return Signal.NEUTRAL


def _erp_signal(pe: float | None, riskfree: float | None) -> Signal | None:
    """Zinsabhängiges ERP-Signal (Fed-Modell-Brücke). None, wenn Daten fehlen."""
    ey = earnings_yield(pe)
    erp = equity_risk_premium(ey, riskfree)
    if erp is None:
        return None
    if erp < _ERP_BEARISH:
        return Signal.BEARISH
    if erp >= _ERP_BULLISH:
        return Signal.BULLISH
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

            pe        = info.get("trailingPE")
            fwd_pe    = info.get("forwardPE")
            div_y     = info.get("dividendYield")
            ev_ebitda = info.get("enterpriseToEbitda")
            riskfree  = info.get("riskFreeRate")
            price     = info.get("regularMarketPrice") or info.get("currentPrice")
            eps_10y_real = info.get("eps10yReal") or []

            cape = shiller_cape(price, eps_10y_real) if eps_10y_real else None

            # Zinsabhängiges ERP-Signal bevorzugen; Fallback: symmetrische PE-Range.
            erp_sig = _erp_signal(pe, riskfree)
            signal = erp_sig if erp_sig is not None else _signal(pe, ticker)

            result = IndexValuationSnapshot(
                pe_trailing=round(pe, 2) if pe is not None else None,
                pe_forward=round(fwd_pe, 2) if fwd_pe is not None else None,
                shiller_cape=round(cape, 2) if cape is not None else None,
                dividend_yield=round(div_y * 100, 2) if div_y is not None else None,
                ev_ebitda=round(ev_ebitda, 2) if ev_ebitda is not None else None,
                signal=signal,
            )
        except Exception:
            return _DEFAULT

        self.bus.publish(IndexValuationReady(source="index_valuation_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> IndexValuationSnapshot:
        return _DEFAULT
