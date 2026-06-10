import asyncio
import statistics

from core.domain.events import ValuationRangeReady
from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
from core.ports.data_provider import FundamentalsProvider, MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = ValuationRangeSnapshot(
    methods=[], combined_low=0.0, combined_high=0.0,
    current_price=None, position="unknown", signal=Signal.NEUTRAL,
)

# Peer-Multiples als Fallback (werden später durch API-Daten ersetzt)
_SECTOR_MULTIPLES: dict[str, dict] = {
    "Technology":  {"pe": (20, 35), "ev_ebitda": (15, 25)},
    "Healthcare":  {"pe": (18, 28), "ev_ebitda": (12, 20)},
    "Financials":  {"pe": (10, 16), "ev_ebitda": (8, 14)},
    "default":     {"pe": (15, 25), "ev_ebitda": (10, 18)},
}


def _combine_methods(methods: list[ValuationMethod]) -> tuple[float, float]:
    """Median der lows/highs — vermeidet künstlich breites Band durch min/max."""
    lows  = sorted(m.low  for m in methods)
    highs = sorted(m.high for m in methods)
    return statistics.median(lows), statistics.median(highs)


def _position(price: float, low: float, high: float) -> tuple[str, Signal]:
    if price < low * 0.95:
        return "undervalued", Signal.BULLISH
    if price > high * 1.05:
        return "overvalued", Signal.BEARISH
    return "fair", Signal.NEUTRAL


class ValuationRangeAgent:
    def __init__(self, fundamentals: FundamentalsProvider, market: MarketDataProvider, bus: EventBus):
        self.fundamentals = fundamentals
        self.market = market
        self.bus = bus

    async def run(self, ticker: str, sector: str = "default") -> ValuationRangeSnapshot:
        # TODO: vollständige Implementierung wenn Finnhub/FMP Adapter bereit
        data = await asyncio.to_thread(self.fundamentals.get_fundamentals, ticker)
        current_price = await asyncio.to_thread(self.market.get_current_price, ticker)

        multiples = _SECTOR_MULTIPLES.get(sector, _SECTOR_MULTIPLES["default"])
        methods: list[ValuationMethod] = []

        # KGV-Multiple
        pe = data.get("pe_ratio")
        eps = data.get("eps")
        if pe is not None and eps is not None:
            pe_low  = eps * multiples["pe"][0]
            pe_high = eps * multiples["pe"][1]
            methods.append(ValuationMethod(name="KGV-Multiple", low=round(pe_low, 2), high=round(pe_high, 2)))

        # EV/EBITDA-Multiple
        ebitda_per_share = data.get("ebitda_per_share")
        net_debt_per_share = data.get("net_debt_per_share", 0)
        if ebitda_per_share:
            ev_low  = ebitda_per_share * multiples["ev_ebitda"][0] - net_debt_per_share
            ev_high = ebitda_per_share * multiples["ev_ebitda"][1] - net_debt_per_share
            methods.append(ValuationMethod(name="EV/EBITDA-Multiple", low=round(ev_low, 2), high=round(ev_high, 2)))

        # DCF (vereinfacht — TODO: vollständiges DCF wenn FCF-Daten verfügbar)
        fcf_per_share = data.get("fcf_per_share")
        wacc = data.get("wacc", 0.09)
        growth = data.get("revenue_cagr_3y", 5) / 100 if data.get("revenue_cagr_3y") else 0.05
        if fcf_per_share is not None and wacc:
            terminal_growth = 0.025
            if abs(wacc - terminal_growth) >= 0.001:
                dcf_low  = fcf_per_share * (1 + growth * 0.7) / (wacc - terminal_growth)
                dcf_high = fcf_per_share * (1 + growth * 1.3) / (wacc - terminal_growth)
                methods.append(ValuationMethod(name="DCF", low=round(dcf_low, 2), high=round(dcf_high, 2)))

        if not methods:
            self.bus.publish(ValuationRangeReady(source="valuation_range_agent", payload={"ticker": ticker}))
            return _DEFAULT

        combined_low, combined_high = _combine_methods(methods)
        position, signal = _position(current_price or 0, combined_low, combined_high)

        result = ValuationRangeSnapshot(
            methods=methods,
            combined_low=combined_low,
            combined_high=combined_high,
            current_price=current_price,
            position=position,
            signal=signal,
        )
        self.bus.publish(ValuationRangeReady(source="valuation_range_agent", payload={
            "ticker": ticker, "position": position,
            "low": combined_low, "high": combined_high,
        }))
        return result

    @staticmethod
    def default() -> ValuationRangeSnapshot:
        return _DEFAULT
