import asyncio

from agents.market_cockpit.macro.inflation_agent import InflationAgent
from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from agents.market_cockpit.macro.gdp_agent import GDPAgent
from agents.market_cockpit.macro.shiller_cape_agent import ShillerCAPEAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.commodity.energy_agent import EnergyAgent
from agents.market_cockpit.commodity.industrial_metals_agent import IndustrialMetalsAgent
from agents.market_cockpit.commodity.precious_metals_macro_agent import PreciousMetalsMacroAgent
from agents.market_cockpit.commodity.agricultural_agent import AgriculturalAgent
from agents.market_cockpit.sentiment.vix_agent import VIXAgent
from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent
from agents.market_cockpit.sentiment.put_call_agent import PutCallAgent
from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent
from agents.market_cockpit.yield_curve.sovereign_spread_agent import SovereignSpreadAgent
from agents.market_cockpit.sector.sector_performance_agent import SectorPerformanceAgent
from agents.market_cockpit.sector.sector_rotation_agent import SectorRotationAgent
from core.domain.models import (
    CockpitResult, MacroChiefResult, CommodityChiefResult, SentimentChiefResult,
    YieldCurveChiefResult, SectorChiefResult,
)
from core.domain.regime import RegimeDetector
from core.ports.data_provider import MacroDataProvider, EcbDataProvider, SnbDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus


class TopDownOrchestrator:
    """
    Modus 1 — Top-Down Analyse.
    Koordiniert alle Agents direkt und gibt ein CockpitResult zurück.
    """

    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
    ):
        self._macro    = macro
        self._detector = RegimeDetector()

        self.inflation_agent     = InflationAgent(macro, ecb, snb, bus)
        self.money_supply_agent  = MoneySupplyAgent(macro, ecb, snb, bus)
        self.interest_rate_agent = InterestRateAgent(macro, ecb, snb, bus)
        self.gdp_agent           = GDPAgent(macro, ecb, snb, bus)
        self.shiller_cape_agent  = ShillerCAPEAgent(market, bus)
        self.labor_income_agent  = LaborIncomeAgent(macro, bus)
        self.credit_agent        = CreditAgent(macro, bus)

        self.energy_agent          = EnergyAgent(market, bus)
        self.industrial_agent      = IndustrialMetalsAgent(market, bus)
        self.precious_metals_agent = PreciousMetalsMacroAgent(market, bus)
        self.agricultural_agent    = AgriculturalAgent(market, bus)

        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus)
        self.put_call_agent   = PutCallAgent(market, bus)

        self.yield_spread_agent     = YieldSpreadAgent(macro, ecb, snb, bus)
        self.sovereign_spread_agent = SovereignSpreadAgent(ecb, bus)

        self.sector_performance_agent = SectorPerformanceAgent(market, bus)
        self.sector_rotation_agent    = SectorRotationAgent(bus)

    async def run(self) -> CockpitResult:
        (
            inflation, money_supply, interest_rate, gdp, shiller_cape, labor_income, credit,
            energy, industrial_metals, precious_metals, agricultural,
            vix, fear_greed, put_call,
            yield_spreads, sovereign_spreads,
            sector_performance,
            state,
        ) = await asyncio.gather(
            self.inflation_agent.run(),
            self.money_supply_agent.run(),
            self.interest_rate_agent.run(),
            self.gdp_agent.run(),
            self.shiller_cape_agent.run(),
            self.labor_income_agent.run(),
            self.credit_agent.run(),
            self.energy_agent.run(),
            self.industrial_agent.run(),
            self.precious_metals_agent.run(),
            self.agricultural_agent.run(),
            self.vix_agent.run(),
            self.fear_greed_agent.run(),
            self.put_call_agent.run(),
            self.yield_spread_agent.run(),
            self.sovereign_spread_agent.run(),
            self.sector_performance_agent.run(),
            asyncio.to_thread(self._macro.get_economic_state),
            return_exceptions=True,
        )

        def _safe(r, default): return default if isinstance(r, Exception) else r

        inflation         = _safe(inflation,         InflationAgent.default())
        money_supply      = _safe(money_supply,      MoneySupplyAgent.default())
        interest_rate     = _safe(interest_rate,     InterestRateAgent.default())
        gdp               = _safe(gdp,               GDPAgent.default())
        shiller_cape      = _safe(shiller_cape,      ShillerCAPEAgent.default())
        labor_income      = _safe(labor_income,       LaborIncomeAgent.default())
        credit            = _safe(credit,            CreditAgent.default())
        energy            = _safe(energy,            EnergyAgent.default())
        industrial_metals = _safe(industrial_metals, IndustrialMetalsAgent.default())
        precious_metals   = _safe(precious_metals,   PreciousMetalsMacroAgent.default())
        agricultural      = _safe(agricultural,      AgriculturalAgent.default())
        vix               = _safe(vix,               VIXAgent.default())
        fear_greed        = _safe(fear_greed,        FearGreedAgent.default())
        put_call          = _safe(put_call,          PutCallAgent.default())
        yield_spreads     = _safe(yield_spreads,     YieldSpreadAgent.default())
        sovereign_spreads = _safe(sovereign_spreads, SovereignSpreadAgent.default())
        sector_performance = _safe(sector_performance, SectorPerformanceAgent.default())
        state             = _safe(state,             {})

        regime, confidence, _ = self._detector.detect(state)
        sector_rotation = self.sector_rotation_agent.run(regime, sector_performance.leading_usa)

        return CockpitResult(
            macro=MacroChiefResult(
                regime=regime,
                regime_confidence=confidence,
                inflation=inflation,
                money_supply=money_supply,
                interest_rate=interest_rate,
                gdp=gdp,
                shiller_cape=shiller_cape,
                labor_income=labor_income,
                credit=credit,
            ),
            commodities=CommodityChiefResult(
                energy=energy,
                industrial_metals=industrial_metals,
                precious_metals=precious_metals,
                agricultural=agricultural,
            ),
            sentiment=SentimentChiefResult(
                vix=vix,
                fear_greed=fear_greed,
                put_call=put_call,
            ),
            yield_curve=YieldCurveChiefResult(
                yield_spreads=yield_spreads,
                sovereign_spreads=sovereign_spreads,
            ),
            sectors=SectorChiefResult(
                performance=sector_performance,
                rotation=sector_rotation,
            ),
        )
