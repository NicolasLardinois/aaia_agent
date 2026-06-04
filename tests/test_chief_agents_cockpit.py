from core.domain.models import EquityChiefResult, Signal
from core.domain.models import FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot
from core.domain.models import InsiderSnapshot, EarningsTrendSnapshot, MoatSnapshot, MoatScore, ValuationRangeSnapshot
from core.domain.events import (
    MacroChiefReady, CommodityChiefReady, SentimentChiefReady,
    YieldCurveChiefReady, SectorChiefReady,
    EquityChiefReady, BondChiefReady, IndexChiefReady,
    CommodityBottomUpChiefReady, PreciousMetalsChiefReady,
    AnomalyChiefReady, JudgmentChiefReady, BacktesterChiefReady,
)


def test_equity_chief_result_fields():
    result = EquityChiefResult(
        fundamentals=FundamentalsSnapshot(
            pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
            ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
            price_fcf=None, dividend_yield=None, wacc=None,
            revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
            debt_to_equity=None, signal=Signal.NEUTRAL,
        ),
        quality=QualitySnapshot(
            gross_margin=None, operating_margin=None, net_margin=None,
            fcf_margin=None, roe=None, roa=None, roic=None,
            debt_to_equity=None, net_debt_ebitda=None, interest_coverage=None,
            current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
        ),
        short_interest=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL),
        insider=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL),
        earnings_trend=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL),
        moat=MoatSnapshot(
            intangible_assets=MoatScore(score=0, evidence=""),
            switching_costs=MoatScore(score=0, evidence=""),
            network_effects=MoatScore(score=0, evidence=""),
            cost_advantages=MoatScore(score=0, evidence=""),
            efficient_scale=MoatScore(score=0, evidence=""),
            total_score=0, overall="none", llm_reasoning="", signal=Signal.NEUTRAL,
        ),
        valuation_range=ValuationRangeSnapshot(
            methods=[], combined_low=0.0, combined_high=0.0,
            current_price=None, position="unknown", signal=Signal.NEUTRAL,
        ),
    )
    assert result.fundamentals.signal == Signal.NEUTRAL
    assert result.moat.overall == "none"


def test_chief_events_importable():
    e = CommodityChiefReady(source="test", payload={})
    assert e.source == "test"
