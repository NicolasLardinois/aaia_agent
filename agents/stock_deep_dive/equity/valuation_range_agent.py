import asyncio
import statistics

from core.domain.events import ValuationRangeReady
from core.domain.models import ValuationRangeSnapshot, ValuationMethod, Signal
from core.ports.data_provider import FundamentalsProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.valuation_math import two_stage_dcf, capm_wacc

_DEFAULT = ValuationRangeSnapshot(
    methods=[], combined_low=0.0, combined_high=0.0,
    current_price=None, position="unknown", signal=Signal.NEUTRAL,
)

# Langfristige Wachstumsrate für DCF-Terminal-Value (nach Planungshorizont)
# Kein Sektor wächst dauerhaft schneller als die Gesamtwirtschaft — Werte nahe BIP-Wachstum
_TERMINAL_GROWTH: dict[str, float] = {
    "Technology":  0.030,   # Innovationsprämie über BIP
    "Healthcare":  0.030,   # Demografischer Rückenwind
    "Financials":  0.025,
    "Energy":      0.025,   # Energieverbrauch wächst mit Wirtschaft (unabhängig von Quelle)
    "default":     0.025,
}

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

        multiples       = _SECTOR_MULTIPLES.get(sector, _SECTOR_MULTIPLES["default"])
        terminal_growth = _TERMINAL_GROWTH.get(sector, _TERMINAL_GROWTH["default"])
        methods: list[ValuationMethod] = []

        # KGV-Multiple — nur bei positivem EPS (negatives EPS → invertiertes Band)
        pe = data.get("pe_ratio")
        eps = data.get("eps")
        if pe is not None and pe > 0 and eps is not None and eps > 0:
            pe_low  = eps * multiples["pe"][0]
            pe_high = eps * multiples["pe"][1]
            methods.append(ValuationMethod(name="KGV-Multiple", low=round(pe_low, 2), high=round(pe_high, 2)))

        # EV/EBITDA-Multiple — nur bei positivem EBITDA (negatives EBITDA → negatives Band)
        ebitda_per_share = data.get("ebitda_per_share")
        net_debt_per_share = data.get("net_debt_per_share", 0)
        if ebitda_per_share is not None and ebitda_per_share > 0:
            ev_low  = ebitda_per_share * multiples["ev_ebitda"][0] - net_debt_per_share
            ev_high = ebitda_per_share * multiples["ev_ebitda"][1] - net_debt_per_share
            methods.append(ValuationMethod(name="EV/EBITDA-Multiple", low=round(ev_low, 2), high=round(ev_high, 2)))

        # DCF — echtes 2-Stufen-DCF mit CAPM-WACC; nur bei positivem FCF (neg. FCF → neg. Fair Value)
        fcf_per_share = data.get("fcf_per_share")
        if fcf_per_share is not None and fcf_per_share > 0:
            wacc = capm_wacc(
                rf=data.get("risk_free_rate", 0.04),
                beta=data.get("beta", 1.0),
                erp=data.get("erp", 0.05),
                cost_of_debt=data.get("cost_of_debt", 0.05),
                tax_rate=data.get("tax_rate", 0.21),
                equity_weight=data.get("equity_weight", 0.8),
                debt_weight=data.get("debt_weight", 0.2),
            )
            _cagr = data.get("revenue_cagr_3y")
            growth = (_cagr if _cagr is not None else 5) / 100
            # Szenario-Band: konservativer (0.7×) bis optimistischer (1.3×) Wachstumspfad
            dcf_low = two_stage_dcf(
                fcf0=fcf_per_share, growth=growth * 0.7,
                terminal_growth=terminal_growth, wacc=wacc, years=5,
            )
            dcf_high = two_stage_dcf(
                fcf0=fcf_per_share, growth=growth * 1.3,
                terminal_growth=terminal_growth, wacc=wacc, years=5,
            )
            lo, hi = min(dcf_low, dcf_high), max(dcf_low, dcf_high)
            methods.append(ValuationMethod(name="DCF", low=round(lo, 2), high=round(hi, 2)))

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
