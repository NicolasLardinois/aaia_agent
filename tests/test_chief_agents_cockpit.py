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


# ─────────────────────────────────────────────
# Task 3: CommodityChiefAgentMakro
# ─────────────────────────────────────────────

from agents.market_cockpit.commodity_chief_agent import CommodityChiefAgentMakro
from core.domain.models import CommodityChiefResult, EnergySnapshot, IndustrialMetalsSnapshot, PreciousMetalsMacroSnapshot, AgriculturalSnapshot

def _neutral_energy():
    return EnergySnapshot(wti_usd=None, brent_usd=None, natural_gas_usd=None, signal=Signal.NEUTRAL)

def _neutral_industrial():
    return IndustrialMetalsSnapshot(copper_usd=None, aluminium_usd=None, zinc_usd=None, nickel_usd=None, signal=Signal.NEUTRAL)

def _neutral_precious_macro():
    return PreciousMetalsMacroSnapshot(gold_usd=None, silver_usd=None, platinum_usd=None, palladium_usd=None, gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL)

def _neutral_agricultural():
    return AgriculturalSnapshot(wheat_usd=None, corn_usd=None, soy_usd=None, coffee_usd=None, sugar_usd=None, cotton_usd=None, orange_juice_usd=None, signal=Signal.NEUTRAL)


def test_commodity_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgentMakro(market, bus)
    chief.energy_agent.run           = AsyncMock(return_value=_neutral_energy())
    chief.industrial_agent.run       = AsyncMock(return_value=_neutral_industrial())
    chief.precious_metals_agent.run  = AsyncMock(return_value=_neutral_precious_macro())
    chief.agricultural_agent.run     = AsyncMock(return_value=_neutral_agricultural())

    result = asyncio.run(chief.run())
    assert isinstance(result, CommodityChiefResult)
    bus.publish.assert_called_once()


def test_commodity_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgentMakro(market, bus)
    chief.energy_agent.run           = AsyncMock(side_effect=RuntimeError("timeout"))
    chief.industrial_agent.run       = AsyncMock(return_value=_neutral_industrial())
    chief.precious_metals_agent.run  = AsyncMock(return_value=_neutral_precious_macro())
    chief.agricultural_agent.run     = AsyncMock(return_value=_neutral_agricultural())

    result = asyncio.run(chief.run())
    assert isinstance(result, CommodityChiefResult)


def test_commodity_chief_default():
    result = CommodityChiefAgentMakro.default()
    assert isinstance(result, CommodityChiefResult)


# ─────────────────────────────────────────────
# Task 4: SentimentChiefAgent
# ─────────────────────────────────────────────

from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from core.domain.models import SentimentChiefResult, VIXSnapshot, FearGreedSnapshot, PutCallSnapshot

def test_sentiment_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = SentimentChiefAgent(market, bus)
    chief.vix_agent.run        = AsyncMock(return_value=VIXSnapshot(vix=None, vstoxx=None, signal=Signal.NEUTRAL))
    chief.fear_greed_agent.run = AsyncMock(return_value=FearGreedSnapshot(value=None, label="Neutral", signal=Signal.NEUTRAL))
    chief.put_call_agent.run   = AsyncMock(return_value=PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, SentimentChiefResult)
    bus.publish.assert_called_once()


def test_sentiment_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = SentimentChiefAgent(market, bus)
    chief.vix_agent.run        = AsyncMock(side_effect=RuntimeError("down"))
    chief.fear_greed_agent.run = AsyncMock(return_value=FearGreedSnapshot(value=None, label="Neutral", signal=Signal.NEUTRAL))
    chief.put_call_agent.run   = AsyncMock(return_value=PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, SentimentChiefResult)


def test_sentiment_chief_default():
    result = SentimentChiefAgent.default()
    assert isinstance(result, SentimentChiefResult)


# ─────────────────────────────────────────────
# Task 5: YieldCurveChiefAgent
# ─────────────────────────────────────────────

from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from core.domain.models import YieldCurveChiefResult, YieldSpreadSnapshot, SovereignSpreadSnapshot, YieldSpreadDataPoint

def _neutral_yield_spread():
    dp = YieldSpreadDataPoint(spread_10y2y=None, spread_10y3m=None, spread_30y10y=None, inverted=False, signal=Signal.NEUTRAL)
    return YieldSpreadSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def test_yield_curve_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    ecb = MagicMock()
    snb = MagicMock()
    chief = YieldCurveChiefAgent(macro, ecb, snb, bus)
    chief.yield_spread_agent.run     = AsyncMock(return_value=_neutral_yield_spread())
    chief.sovereign_spread_agent.run = AsyncMock(return_value=SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, YieldCurveChiefResult)
    bus.publish.assert_called_once()


def test_yield_curve_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    ecb = MagicMock()
    snb = MagicMock()
    chief = YieldCurveChiefAgent(macro, ecb, snb, bus)
    chief.yield_spread_agent.run     = AsyncMock(side_effect=RuntimeError("timeout"))
    chief.sovereign_spread_agent.run = AsyncMock(return_value=SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, YieldCurveChiefResult)


def test_yield_curve_chief_default():
    result = YieldCurveChiefAgent.default()
    assert isinstance(result, YieldCurveChiefResult)


# ─────────────────────────────────────────────
# Task 6: SectorChiefAgent
# ─────────────────────────────────────────────

from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.models import SectorChiefResult, SectorPerformanceSnapshot

def _neutral_sector_performance():
    return SectorPerformanceSnapshot(
        usa={}, eurozone={},
        leading_usa="Technology", lagging_usa="Utilities",
        leading_eu="Technology", lagging_eu="Utilities",
    )

def test_sector_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = SectorChiefAgent(market, bus)
    chief.sector_performance_agent.run = AsyncMock(return_value=_neutral_sector_performance())
    # sector_rotation_agent.run is synchronous — mock it to isolate the chief's publish call
    from core.domain.models import SectorRotationSnapshot
    chief.sector_rotation_agent.run = MagicMock(
        return_value=SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)
    )

    result = asyncio.run(chief.run(MarketRegime.EXPANSION))
    assert isinstance(result, SectorChiefResult)
    bus.publish.assert_called_once()


def test_sector_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = SectorChiefAgent(market, bus)
    chief.sector_performance_agent.run = AsyncMock(side_effect=RuntimeError("down"))

    result = asyncio.run(chief.run(MarketRegime.EXPANSION))
    assert isinstance(result, SectorChiefResult)


def test_sector_chief_default():
    result = SectorChiefAgent.default()
    assert isinstance(result, SectorChiefResult)
