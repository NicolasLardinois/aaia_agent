import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from core.domain.models import (
    EquityChiefResult, Signal,
    FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot,
    InsiderSnapshot, EarningsTrendSnapshot, MoatSnapshot, MoatScore,
    ValuationRangeSnapshot,
)

def _neutral_fundamentals():
    return FundamentalsSnapshot(
        pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
        ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
        price_fcf=None, dividend_yield=None, wacc=None,
        revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
        debt_to_equity=None, signal=Signal.NEUTRAL,
    )

def _neutral_quality():
    return QualitySnapshot(
        gross_margin=None, operating_margin=None, net_margin=None,
        fcf_margin=None, roe=None, roa=None, roic=None,
        debt_to_equity=None, net_debt_ebitda=None, interest_coverage=None,
        current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
    )

def _neutral_moat():
    s = MoatScore(score=0, evidence="")
    return MoatSnapshot(
        intangible_assets=s, switching_costs=s, network_effects=s,
        cost_advantages=s, efficient_scale=s,
        total_score=0, overall="none", llm_reasoning="", signal=Signal.NEUTRAL,
    )

def _neutral_valuation_range():
    return ValuationRangeSnapshot(
        methods=[], combined_low=0.0, combined_high=0.0,
        current_price=None, position="unknown", signal=Signal.NEUTRAL,
    )


def test_equity_chief_returns_result():
    bus = MagicMock()
    fundamentals = MagicMock()
    market = MagicMock()
    llm = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)
    chief.fundamentals_agent.run    = AsyncMock(return_value=_neutral_fundamentals())
    chief.quality_agent.run         = AsyncMock(return_value=_neutral_quality())
    chief.short_agent.run           = AsyncMock(return_value=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL))
    chief.insider_agent.run         = AsyncMock(return_value=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL))
    chief.earnings_agent.run        = AsyncMock(return_value=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL))
    chief.moat_agent.run            = AsyncMock(return_value=_neutral_moat())
    chief.valuation_range_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("AAPL", "technology"))
    assert isinstance(result, EquityChiefResult)
    bus.publish.assert_called_once()


def test_equity_chief_resilience():
    bus = MagicMock()
    fundamentals = MagicMock()
    market = MagicMock()
    llm = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)
    chief.fundamentals_agent.run    = AsyncMock(side_effect=RuntimeError("API down"))
    chief.quality_agent.run         = AsyncMock(return_value=_neutral_quality())
    chief.short_agent.run           = AsyncMock(return_value=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL))
    chief.insider_agent.run         = AsyncMock(return_value=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL))
    chief.earnings_agent.run        = AsyncMock(return_value=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL))
    chief.moat_agent.run            = AsyncMock(return_value=_neutral_moat())
    chief.valuation_range_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("AAPL", "technology"))
    assert isinstance(result, EquityChiefResult)


def test_equity_chief_default():
    result = EquityChiefAgent.default()
    assert isinstance(result, EquityChiefResult)


# ---------------------------------------------------------------------------
# Task 9: BondChiefAgent
# ---------------------------------------------------------------------------

from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from core.domain.models import (
    BondResult, BondMetricsSnapshot, BondDurationSnapshot,
    BondCreditSnapshot, BondSpreadSnapshot,
)

def _neutral_bond_metrics():
    return BondMetricsSnapshot(
        bond_type="government", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None,
        real_yield=None, country=None, breakeven_inflation=None,
        issuer=None, sector=None, signal=Signal.NEUTRAL,
    )

def _neutral_bond_duration():
    return BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)

def _neutral_bond_credit():
    return BondCreditSnapshot(moodys=None, sp=None, fitch=None, category="investment_grade", trend="stable", default_probability=None, signal=Signal.NEUTRAL)

def _neutral_bond_spread():
    return BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)


def test_bond_chief_returns_result():
    bus = MagicMock()
    fundamentals = MagicMock()
    macro = MagicMock()
    chief = BondChiefAgent(fundamentals, macro, bus)
    chief.bond_metrics_agent.run   = AsyncMock(return_value=_neutral_bond_metrics())
    chief.bond_duration_agent.run  = AsyncMock(return_value=_neutral_bond_duration())
    chief.bond_credit_agent.run    = AsyncMock(return_value=_neutral_bond_credit())
    chief.bond_spread_agent.run    = AsyncMock(return_value=_neutral_bond_spread())

    result = asyncio.run(chief.run("US10Y", "government", "stable"))
    assert isinstance(result, BondResult)
    bus.publish.assert_called_once()


def test_bond_chief_resilience():
    bus = MagicMock()
    fundamentals = MagicMock()
    macro = MagicMock()
    chief = BondChiefAgent(fundamentals, macro, bus)
    chief.bond_metrics_agent.run   = AsyncMock(side_effect=RuntimeError("down"))
    chief.bond_duration_agent.run  = AsyncMock(return_value=_neutral_bond_duration())
    chief.bond_credit_agent.run    = AsyncMock(return_value=_neutral_bond_credit())
    chief.bond_spread_agent.run    = AsyncMock(return_value=_neutral_bond_spread())

    result = asyncio.run(chief.run("US10Y", "government", "stable"))
    assert isinstance(result, BondResult)


def test_bond_chief_default():
    result = BondChiefAgent.default("US10Y", "government")
    assert isinstance(result, BondResult)


# ---------------------------------------------------------------------------
# Task 10: IndexChiefAgent
# ---------------------------------------------------------------------------

from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from core.domain.models import (
    IndexResult, IndexPriceSnapshot, IndexValuationSnapshot, IndexEarningsSnapshot,
    IndexBreadthSnapshot, IndexMomentumSnapshot, SectorCompositionSnapshot, IndexValuationRangeSnapshot,
)

def _neutral_index_price():
    return IndexPriceSnapshot(current_price=None, perf_1w=None, perf_1m=None, perf_3m=None, perf_ytd=None, perf_1y=None, perf_3y=None, perf_5y=None, high_52w=None, low_52w=None, signal=Signal.NEUTRAL)

def _neutral_index_valuation():
    return IndexValuationSnapshot(pe_trailing=None, pe_forward=None, shiller_cape=None, dividend_yield=None, ev_ebitda=None, signal=Signal.NEUTRAL)

def _neutral_index_earnings():
    return IndexEarningsSnapshot(eps_growth_1y=None, revenue_growth_1y=None, operating_margin=None, estimate_revision="stable", signal=Signal.NEUTRAL)

def _neutral_index_breadth():
    return IndexBreadthSnapshot(pct_above_ma50=None, pct_above_ma200=None, advance_decline_ratio=None, new_highs=None, new_lows=None, signal=Signal.NEUTRAL)

def _neutral_index_momentum():
    return IndexMomentumSnapshot(rsi_14=None, ma50=None, ma200=None, golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL)

def _neutral_sector_composition():
    return SectorCompositionSnapshot(top_sector=None, top_sector_weight=None, top_holding=None, top_holding_weight=None, top_10_concentration=None, signal=Signal.NEUTRAL)

def _neutral_index_valuation_range():
    return IndexValuationRangeSnapshot(eps_estimate=None, pe_historical_low=None, pe_historical_high=None, price_low=None, price_mid=None, price_high=None, current_price=None, position="fair", signal=Signal.NEUTRAL)


def test_index_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = IndexChiefAgent(market, bus)
    chief.index_price_agent.run           = AsyncMock(return_value=_neutral_index_price())
    chief.index_valuation_agent.run       = AsyncMock(return_value=_neutral_index_valuation())
    chief.index_earnings_agent.run        = AsyncMock(return_value=_neutral_index_earnings())
    chief.index_breadth_agent.run         = AsyncMock(return_value=_neutral_index_breadth())
    chief.index_momentum_agent.run        = AsyncMock(return_value=_neutral_index_momentum())
    chief.sector_composition_agent.run    = AsyncMock(return_value=_neutral_sector_composition())
    chief.index_valuation_range_agent.run = AsyncMock(return_value=_neutral_index_valuation_range())

    result = asyncio.run(chief.run("SPY"))
    assert isinstance(result, IndexResult)
    bus.publish.assert_called_once()


def test_index_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = IndexChiefAgent(market, bus)
    chief.index_price_agent.run           = AsyncMock(side_effect=RuntimeError("down"))
    chief.index_valuation_agent.run       = AsyncMock(return_value=_neutral_index_valuation())
    chief.index_earnings_agent.run        = AsyncMock(return_value=_neutral_index_earnings())
    chief.index_breadth_agent.run         = AsyncMock(return_value=_neutral_index_breadth())
    chief.index_momentum_agent.run        = AsyncMock(return_value=_neutral_index_momentum())
    chief.sector_composition_agent.run    = AsyncMock(return_value=_neutral_sector_composition())
    chief.index_valuation_range_agent.run = AsyncMock(return_value=_neutral_index_valuation_range())

    result = asyncio.run(chief.run("SPY"))
    assert isinstance(result, IndexResult)


def test_index_chief_default():
    result = IndexChiefAgent.default("SPY")
    assert isinstance(result, IndexResult)


# ---------------------------------------------------------------------------
# Task 11: CommodityChiefAgent (Stock Deep Dive)
# ---------------------------------------------------------------------------

from agents.stock_deep_dive.commodity_chief_agent import CommodityChiefAgentMikro
from core.domain.models import (
    CommodityBottomUpResult, SupplyDemandSnapshot, SeasonalitySnapshot,
    COTSnapshot, CommodityValuationRangeSnapshot,
)

def _neutral_supply_demand():
    return SupplyDemandSnapshot(inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None, production_change_yoy=None, stock_to_flow=None, stock_to_flow_signal=None, signal=Signal.NEUTRAL)

def _neutral_seasonality():
    return SeasonalitySnapshot(current_month_bias="neutral", avg_return_this_month=None, positive_years_pct=None, signal=Signal.NEUTRAL)

def _neutral_cot():
    return COTSnapshot(net_speculative_long=None, net_speculative_pct_oi=None, signal=Signal.NEUTRAL)

def _neutral_commodity_valuation():
    return CommodityValuationRangeSnapshot(current_price=None, price_low_5y=None, price_high_5y=None, percentile_5y=None, percentile_10y=None, production_cost_low=None, production_cost_high=None, position="fair", signal=Signal.NEUTRAL)


def test_commodity_deep_dive_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgentMikro(market, bus)
    chief.supply_demand_agent.run             = AsyncMock(return_value=_neutral_supply_demand())
    chief.seasonality_agent.run               = AsyncMock(return_value=_neutral_seasonality())
    chief.cot_agent.run                       = AsyncMock(return_value=_neutral_cot())
    chief.commodity_valuation_range_agent.run = AsyncMock(return_value=_neutral_commodity_valuation())

    result = asyncio.run(chief.run("CL=F"))
    assert isinstance(result, CommodityBottomUpResult)
    bus.publish.assert_called_once()


def test_commodity_deep_dive_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgentMikro(market, bus)
    chief.supply_demand_agent.run             = AsyncMock(side_effect=RuntimeError("down"))
    chief.seasonality_agent.run               = AsyncMock(return_value=_neutral_seasonality())
    chief.cot_agent.run                       = AsyncMock(return_value=_neutral_cot())
    chief.commodity_valuation_range_agent.run = AsyncMock(return_value=_neutral_commodity_valuation())

    result = asyncio.run(chief.run("CL=F"))
    assert isinstance(result, CommodityBottomUpResult)


def test_commodity_deep_dive_chief_default():
    result = CommodityChiefAgentMikro.default("CL=F")
    assert isinstance(result, CommodityBottomUpResult)


# ---------------------------------------------------------------------------
# Task 12: PreciousMetalsChiefAgent
# ---------------------------------------------------------------------------

from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import PreciousMetalsResult, PreciousMetalSnapshot, CrossMetalSnapshot

def _neutral_pm_price(metal="GOLD"):
    return PreciousMetalSnapshot(metal=metal, price_usd=None, performance={}, rsi=None, ma50=None, ma200=None, stock_to_flow=None, real_yield_correlation=None, signal=Signal.NEUTRAL)

def _neutral_cross_metal():
    return CrossMetalSnapshot(gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL)


def test_precious_metals_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    market = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    chief.pm_price_agent.run     = AsyncMock(return_value=_neutral_pm_price())
    chief.pm_cross_agent.run     = AsyncMock(return_value=_neutral_cross_metal())
    chief.pm_valuation_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("GOLD"))
    assert isinstance(result, PreciousMetalsResult)
    bus.publish.assert_called_once()


def test_precious_metals_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    market = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    chief.pm_price_agent.run     = AsyncMock(side_effect=RuntimeError("down"))
    chief.pm_cross_agent.run     = AsyncMock(return_value=_neutral_cross_metal())
    chief.pm_valuation_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("GOLD"))
    assert isinstance(result, PreciousMetalsResult)


def test_precious_metals_chief_default():
    result = PreciousMetalsChiefAgent.default("GOLD")
    assert isinstance(result, PreciousMetalsResult)
