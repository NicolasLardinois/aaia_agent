import asyncio

from core.domain.events import FundamentalsReady
from core.domain.models import FundamentalsSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = FundamentalsSnapshot(
    pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
    ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
    price_fcf=None, dividend_yield=None, wacc=None,
    revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
    debt_to_equity=None, signal=Signal.NEUTRAL,
)


def _score(pe, forward_pe, shiller, peg, ev_ebitda, revenue_cagr, op_margin, debt_equity) -> Signal:
    score = 0
    if pe is not None:
        score += 1 if pe < 20 else (-1 if pe > 40 else 0)
    if forward_pe is not None and pe is not None:
        score += 1 if forward_pe < pe else 0
    if shiller is not None:
        # Shiller KGV glättet Konjunkturzyklen → striktere Schwellen als normales KGV
        score += 1 if shiller < 15 else (-1 if shiller > 35 else 0)
    if peg is not None:
        score += 1 if peg < 1.5 else (-1 if peg > 3.0 else 0)
    if ev_ebitda is not None:
        score += 1 if ev_ebitda < 12 else (-1 if ev_ebitda > 25 else 0)
    if revenue_cagr is not None:
        score += 1 if revenue_cagr > 10 else (-1 if revenue_cagr < 0 else 0)
    if op_margin is not None:
        score += 1 if op_margin > 15 else (-1 if op_margin < 0 else 0)
    if debt_equity is not None:
        score += 1 if debt_equity < 0.5 else (-1 if debt_equity > 2.0 else 0)
    return Signal.BULLISH if score >= 3 else (Signal.BEARISH if score <= -2 else Signal.NEUTRAL)


class FundamentalsAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> FundamentalsSnapshot:
        data = await asyncio.to_thread(self.provider.get_fundamentals, ticker)
        pe          = data.get("pe_ratio")
        forward_pe  = data.get("forward_pe")
        shiller     = data.get("shiller_cape")
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
            signal=_score(pe, forward_pe, shiller, peg, ev_ebitda, cagr_3y, op_margin, debt_eq),
        )
        self.bus.publish(FundamentalsReady(source="fundamentals_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> FundamentalsSnapshot:
        return _DEFAULT
