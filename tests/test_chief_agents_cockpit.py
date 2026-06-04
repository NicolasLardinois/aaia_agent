import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from core.domain.models import (
    MacroChiefResult, MarketRegime,
    InflationSnapshot, MoneySupplySnapshot, InterestRateSnapshot,
    GDPSnapshot, ShillerCAPESnapshot, LaborIncomeSnapshot, CreditSnapshot,
    InflationDataPoint, MoneySupplyDataPoint, InterestRateDataPoint,
    GDPDataPoint, ShillerCAPEDataPoint, LaborIncomeDataPoint, CreditDataPoint,
    Signal,
)
from core.domain.models import EquityChiefResult
from core.domain.models import FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot
from core.domain.models import InsiderSnapshot, EarningsTrendSnapshot, MoatSnapshot, MoatScore, ValuationRangeSnapshot
from core.domain.events import (
    MacroChiefReady, CommodityChiefReady, SentimentChiefReady,
    YieldCurveChiefReady, SectorChiefReady,
    EquityChiefReady, BondChiefReady, IndexChiefReady,
    CommodityBottomUpChiefReady, PreciousMetalsChiefReady,
    AnomalyChiefReady, JudgmentChiefReady, BacktesterChiefReady,
)


def _neutral_inflation():
    dp = InflationDataPoint(cpi=None, core_cpi=None, pce=None, ppi=None, real_rate_10y=None, signal=Signal.NEUTRAL)
    return InflationSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_money_supply():
    dp = MoneySupplyDataPoint(m2_growth=None, m3_growth=None, velocity_m2=None, signal=Signal.NEUTRAL)
    return MoneySupplySnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_interest_rate():
    dp = InterestRateDataPoint(policy_rate=None, rate_direction="stable", balance_sheet_growth=None, real_rate=None, signal=Signal.NEUTRAL)
    return InterestRateSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_gdp():
    dp = GDPDataPoint(gdp_growth=None, industrial_production=None, unemployment=None, consumer_sentiment=None, pmi=None, signal=Signal.NEUTRAL)
    return GDPSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_shiller():
    dp = ShillerCAPEDataPoint(cape=None, historical_avg=20.0, deviation_pct=None, signal=Signal.NEUTRAL)
    return ShillerCAPESnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_labor():
    dp = LaborIncomeDataPoint(nominal_wage_growth=None, real_wage_growth=None, signal=Signal.NEUTRAL)
    return LaborIncomeSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_credit():
    dp = CreditDataPoint(credit_growth=None, money_velocity=None, signal=Signal.NEUTRAL)
    return CreditSnapshot(usa=dp, eurozone=dp, switzerland=dp)


def test_macro_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    macro.get_economic_state = MagicMock(return_value={})
    ecb = MagicMock()
    snb = MagicMock()
    market = MagicMock()

    chief = MacroChiefAgent(macro, ecb, snb, market, bus)
    chief.inflation_agent.run     = AsyncMock(return_value=_neutral_inflation())
    chief.money_supply_agent.run  = AsyncMock(return_value=_neutral_money_supply())
    chief.interest_rate_agent.run = AsyncMock(return_value=_neutral_interest_rate())
    chief.gdp_agent.run           = AsyncMock(return_value=_neutral_gdp())
    chief.shiller_cape_agent.run  = AsyncMock(return_value=_neutral_shiller())
    chief.labor_income_agent.run  = AsyncMock(return_value=_neutral_labor())
    chief.credit_agent.run        = AsyncMock(return_value=_neutral_credit())

    result = asyncio.run(chief.run())
    assert isinstance(result, MacroChiefResult)
    assert isinstance(result.regime, MarketRegime)
    bus.publish.assert_called_once()


def test_macro_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    macro.get_economic_state = MagicMock(return_value={})
    ecb = MagicMock()
    snb = MagicMock()
    market = MagicMock()

    chief = MacroChiefAgent(macro, ecb, snb, market, bus)
    chief.inflation_agent.run     = AsyncMock(side_effect=RuntimeError("API down"))
    chief.money_supply_agent.run  = AsyncMock(return_value=_neutral_money_supply())
    chief.interest_rate_agent.run = AsyncMock(return_value=_neutral_interest_rate())
    chief.gdp_agent.run           = AsyncMock(return_value=_neutral_gdp())
    chief.shiller_cape_agent.run  = AsyncMock(return_value=_neutral_shiller())
    chief.labor_income_agent.run  = AsyncMock(return_value=_neutral_labor())
    chief.credit_agent.run        = AsyncMock(return_value=_neutral_credit())

    result = asyncio.run(chief.run())
    assert isinstance(result, MacroChiefResult)  # did not crash


def test_macro_chief_default():
    result = MacroChiefAgent.default()
    assert isinstance(result, MacroChiefResult)
    assert result.regime == MarketRegime.EXPANSION


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
