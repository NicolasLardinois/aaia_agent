import asyncio

from core.domain.events import FundamentalsReady
from core.domain.models import FundamentalsSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.utils.scoring import sector_relative_signal

_DEFAULT = FundamentalsSnapshot(
    pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
    ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
    price_fcf=None, dividend_yield=None, wacc=None,
    revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
    debt_to_equity=None, signal=Signal.NEUTRAL,
)

# Sektor-typische Multiple-Verteilungen als Proxy-Historie (bis Peer-API verfügbar).
# Werte = repräsentative Stützstellen je Sektor → Basis für percentile_rank.
_SECTOR_PE: dict[str, list[float]] = {
    "Technology":  [18, 22, 26, 30, 35, 40],
    "Healthcare":  [14, 18, 22, 26, 30],
    "Financials":  [8, 10, 12, 14, 16],
    "Energy":      [6, 8, 10, 12, 15],
    "default":     [10, 14, 18, 22, 28],
}
_SECTOR_EV_EBITDA: dict[str, list[float]] = {
    "Technology":  [12, 15, 18, 22, 26],
    "Healthcare":  [9, 12, 15, 18, 22],
    "Financials":  [6, 8, 10, 12, 14],
    "Energy":      [4, 6, 8, 10, 12],
    "default":     [8, 10, 13, 16, 20],
}

# Wachstums-Mindestbasis, ab der PEG aussagekräftig ist (Prozentpunkte).
_PEG_MIN_GROWTH = 3.0
# PEG-Schwelle nahe Peter-Lynch-Standard 1.0 (statt großzügiger 1.5).
_PEG_CHEAP = 1.0
_PEG_RICH  = 2.0

_SCORE = {Signal.BULLISH: 1, Signal.NEUTRAL: 0, Signal.BEARISH: -1}


def _score(pe, forward_pe, peg, ev_ebitda, price_fcf, price_book,
           revenue_cagr, op_margin, debt_equity, sector: str = "default") -> Signal:
    score = 0

    # P/E — negatives/None EPS neutralisieren, sonst sektor-relativ
    if pe is not None and pe > 0:
        score += _SCORE[sector_relative_signal(pe, _SECTOR_PE.get(sector, _SECTOR_PE["default"]),
                                                lower_is_better=True)]

    # Forward < Trailing = erwartetes EPS-Wachstum (nur bei positivem Trailing-P/E)
    if forward_pe is not None and pe is not None and pe > 0:
        score += 1 if forward_pe < pe else 0

    # EV/EBITDA — sektor-relativ
    if ev_ebitda is not None and ev_ebitda > 0:
        score += _SCORE[sector_relative_signal(ev_ebitda, _SECTOR_EV_EBITDA.get(sector, _SECTOR_EV_EBITDA["default"]),
                                               lower_is_better=True)]

    # PEG — nur bei sinnvoller Wachstumsbasis, Schwelle ~1.0
    if peg is not None and revenue_cagr is not None and revenue_cagr >= _PEG_MIN_GROWTH:
        score += 1 if peg < _PEG_CHEAP else (-1 if peg > _PEG_RICH else 0)

    # P/FCF — vorher ungenutzt
    if price_fcf is not None and price_fcf > 0:
        score += 1 if price_fcf < 12 else (-1 if price_fcf > 30 else 0)

    # P/B — vorher ungenutzt (relevant v. a. für Financials)
    if price_book is not None and price_book > 0:
        score += 1 if price_book < 1.5 else (-1 if price_book > 5.0 else 0)

    # Wachstum / Marge / Verschuldung
    if revenue_cagr is not None:
        score += 1 if revenue_cagr > 10 else (-1 if revenue_cagr < 0 else 0)
    if op_margin is not None:
        score += 1 if op_margin > 15 else (-1 if op_margin < 0 else 0)
    if debt_equity is not None:
        score += 1 if debt_equity < 0.5 else (-1 if debt_equity > 2.0 else 0)

    # Symmetrische, begründete Schwellen (gleicher Betrag beidseitig)
    return Signal.BULLISH if score >= 3 else (Signal.BEARISH if score <= -3 else Signal.NEUTRAL)


class FundamentalsAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str, sector: str = "default") -> FundamentalsSnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        pe          = data.get("pe_ratio")
        forward_pe  = data.get("forward_pe")
        shiller     = data.get("shiller_cape")   # nur durchgereicht, NICHT im Signal
        peg         = data.get("peg_ratio")
        ev_ebitda   = data.get("ev_ebitda")
        ev_revenue  = data.get("ev_revenue")
        price_book  = data.get("price_book")
        price_sales = data.get("price_sales")
        price_fcf   = data.get("price_fcf")
        div_yield   = data.get("dividend_yield")
        wacc        = data.get("wacc")
        cagr_3y     = data.get("revenue_cagr_3y")
        op_margin   = data.get("operating_margin")
        gross_m     = data.get("gross_margin")
        debt_eq     = data.get("debt_to_equity")

        result = FundamentalsSnapshot(
            pe_ratio=pe, forward_pe=forward_pe, shiller_cape=shiller,
            peg_ratio=peg, ev_ebitda=ev_ebitda, ev_revenue=ev_revenue,
            price_book=price_book, price_sales=price_sales, price_fcf=price_fcf,
            dividend_yield=div_yield, wacc=wacc, revenue_cagr_3y=cagr_3y,
            operating_margin=op_margin, gross_margin=gross_m, debt_to_equity=debt_eq,
            signal=_score(pe, forward_pe, peg, ev_ebitda, price_fcf, price_book,
                          cagr_3y, op_margin, debt_eq, sector=sector),
        )
        self.bus.publish(FundamentalsReady(source="fundamentals_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> FundamentalsSnapshot:
        return _DEFAULT
