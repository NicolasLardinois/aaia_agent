import asyncio

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
from agents.stock_deep_dive.equity.quality_agent import QualityAgent
from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent
from agents.stock_deep_dive.equity.insider_agent import InsiderAgent
from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent
from agents.stock_deep_dive.equity.moat_agent import MoatAgent
from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent
from agents.stock_deep_dive.precious_metals.precious_metal_price_agent import PreciousMetalPriceAgent
from agents.stock_deep_dive.precious_metals.cross_metal_agent import CrossMetalAgent
from agents.stock_deep_dive.precious_metals.precious_metals_valuation_agent import PreciousMetalsValuationAgent
from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from agents.stock_deep_dive.bond.bond_credit_agent import BondCreditAgent
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent
from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent
from agents.stock_deep_dive.index.index_valuation_agent import IndexValuationAgent
from agents.stock_deep_dive.index.index_earnings_agent import IndexEarningsAgent
from agents.stock_deep_dive.index.index_breadth_agent import IndexBreadthAgent
from agents.stock_deep_dive.index.index_momentum_agent import IndexMomentumAgent
from agents.stock_deep_dive.index.sector_composition_agent import SectorCompositionAgent
from agents.stock_deep_dive.index.index_valuation_range_agent import IndexValuationRangeAgent
from agents.stock_deep_dive.commodity.supply_demand_agent import SupplyDemandAgent
from agents.stock_deep_dive.commodity.seasonality_agent import SeasonalityAgent
from agents.stock_deep_dive.commodity.cot_agent import COTAgent
from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import CommodityValuationRangeAgent
from core.domain.models import (
    BottomUpResult, BondResult, IndexResult, CommodityBottomUpResult,
    PreciousMetalsResult, Signal,
)
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class BottomUpOrchestrator:
    """
    Modus 2 — Bottom-Up Analyse.
    Verzweigt intern nach asset_class: equity, bond, oder precious_metal.
    Alle Agenten laufen parallel. Scheitert ein Agent, liefert er einen Standardwert.
    """

    def __init__(
        self,
        fundamentals_provider: FundamentalsProvider,
        macro_provider: MacroDataProvider,
        market_provider: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.fundamentals_agent    = FundamentalsAgent(fundamentals_provider, bus)
        self.quality_agent         = QualityAgent(fundamentals_provider, bus)
        self.short_agent           = ShortInterestAgent(fundamentals_provider, bus)
        self.insider_agent         = InsiderAgent(fundamentals_provider, bus)
        self.earnings_agent        = EarningsTrendAgent(fundamentals_provider, bus)
        self.moat_agent            = MoatAgent(llm, bus)
        self.valuation_range_agent = ValuationRangeAgent(fundamentals_provider, market_provider, bus)

        self.pm_price_agent        = PreciousMetalPriceAgent(market_provider, bus)
        self.pm_cross_agent        = CrossMetalAgent(market_provider, bus)
        self.pm_valuation_agent    = PreciousMetalsValuationAgent(macro_provider, market_provider, bus)

        self.bond_metrics_agent    = BondMetricsAgent(fundamentals_provider, macro_provider, bus)
        self.bond_duration_agent   = BondDurationAgent(fundamentals_provider, bus)
        self.bond_credit_agent     = BondCreditAgent(fundamentals_provider, bus)
        self.bond_spread_agent     = BondSpreadAgent(fundamentals_provider, bus)

        self.index_price_agent        = IndexPriceAgent(market_provider, bus)
        self.index_valuation_agent    = IndexValuationAgent(market_provider, bus)
        self.index_earnings_agent     = IndexEarningsAgent(market_provider, bus)
        self.index_breadth_agent      = IndexBreadthAgent(market_provider, bus)
        self.index_momentum_agent     = IndexMomentumAgent(market_provider, bus)
        self.sector_composition_agent = SectorCompositionAgent(market_provider, bus)
        self.index_valuation_range_agent = IndexValuationRangeAgent(market_provider, bus)

        self.supply_demand_agent          = SupplyDemandAgent(bus)
        self.seasonality_agent            = SeasonalityAgent(market_provider, bus)
        self.cot_agent                    = COTAgent(bus)
        self.commodity_valuation_range_agent = CommodityValuationRangeAgent(market_provider, bus)

    async def run(
        self,
        ticker: str,
        asset_class: str = "equity",
        sector: str = "default",
        bond_type: str = "government",
        rate_direction: str = "stable",
    ) -> BottomUpResult:
        if asset_class == "precious_metal":
            return await self._run_precious_metals(ticker)
        if asset_class == "bond":
            return await self._run_bond(ticker, bond_type, rate_direction)
        if asset_class == "index":
            return await self._run_index(ticker)
        if asset_class == "commodity":
            return await self._run_commodity(ticker)
        return await self._run_equity(ticker, asset_class, sector)

    async def _run_equity(self, ticker: str, asset_class: str, sector: str) -> BottomUpResult:
        results = await asyncio.gather(
            self.fundamentals_agent.run(ticker),
            self.quality_agent.run(ticker),
            self.short_agent.run(ticker),
            self.insider_agent.run(ticker),
            self.earnings_agent.run(ticker),
            self.moat_agent.run(ticker),
            self.valuation_range_agent.run(ticker, sector),
            return_exceptions=True,
        )
        fundamentals, quality, short_interest, insider, earnings_trend, moat, valuation_range = [
            r if not isinstance(r, Exception) else default
            for r, default in zip(results, [
                FundamentalsAgent.default(),
                QualityAgent.default(),
                ShortInterestAgent.default(),
                InsiderAgent.default(),
                EarningsTrendAgent.default(),
                MoatAgent.default(),
                ValuationRangeAgent.default(),
            ])
        ]
        return BottomUpResult(
            ticker=ticker,
            asset_class=asset_class,
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=valuation_range,
            precious_metals=None,
            bond=None,
            index=None,
            commodity_deep=None,
        )

    async def _run_bond(self, ticker: str, bond_type: str, rate_direction: str) -> BottomUpResult:
        results = await asyncio.gather(
            self.bond_metrics_agent.run(ticker, bond_type),
            self.bond_duration_agent.run(ticker, rate_direction),
            self.bond_credit_agent.run(ticker),
            self.bond_spread_agent.run(ticker),
            return_exceptions=True,
        )
        metrics, duration, credit, spread = [
            r if not isinstance(r, Exception) else default
            for r, default in zip(results, [
                BondMetricsAgent.default(),
                BondDurationAgent.default(),
                BondCreditAgent.default(),
                BondSpreadAgent.default(),
            ])
        ]
        bond_result = BondResult(
            ticker=ticker,
            bond_type=bond_type,
            metrics=metrics,
            duration=duration,
            credit=credit,
            spread=spread,
        )
        return BottomUpResult(
            ticker=ticker,
            asset_class="bond",
            fundamentals=None,
            quality=None,
            short_interest=None,
            insider=None,
            earnings_trend=None,
            moat=None,
            valuation_range=None,
            precious_metals=None,
            bond=bond_result,
            index=None,
            commodity_deep=None,
        )

    async def _run_index(self, ticker: str) -> BottomUpResult:
        results = await asyncio.gather(
            self.index_price_agent.run(ticker),
            self.index_valuation_agent.run(ticker),
            self.index_earnings_agent.run(ticker),
            self.index_breadth_agent.run(ticker),
            self.index_momentum_agent.run(ticker),
            self.sector_composition_agent.run(ticker),
            self.index_valuation_range_agent.run(ticker),
            return_exceptions=True,
        )
        price, valuation, earnings, breadth, momentum, composition, valuation_range = [
            r if not isinstance(r, Exception) else default
            for r, default in zip(results, [
                IndexPriceAgent.default(),
                IndexValuationAgent.default(),
                IndexEarningsAgent.default(),
                IndexBreadthAgent.default(),
                IndexMomentumAgent.default(),
                SectorCompositionAgent.default(),
                IndexValuationRangeAgent.default(),
            ])
        ]
        index_result = IndexResult(
            ticker=ticker,
            price=price,
            valuation=valuation,
            earnings=earnings,
            breadth=breadth,
            momentum=momentum,
            composition=composition,
            valuation_range=valuation_range,
        )
        return BottomUpResult(
            ticker=ticker, asset_class="index",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=None, precious_metals=None, bond=None,
            index=index_result, commodity_deep=None,
        )

    async def _run_commodity(self, ticker: str) -> BottomUpResult:
        results = await asyncio.gather(
            self.supply_demand_agent.run(ticker),
            self.seasonality_agent.run(ticker),
            self.cot_agent.run(ticker),
            self.commodity_valuation_range_agent.run(ticker),
            return_exceptions=True,
        )
        supply_demand, seasonality, cot, valuation_range = [
            r if not isinstance(r, Exception) else default
            for r, default in zip(results, [
                SupplyDemandAgent.default(),
                SeasonalityAgent.default(),
                COTAgent.default(),
                CommodityValuationRangeAgent.default(),
            ])
        ]
        commodity_result = CommodityBottomUpResult(
            commodity=ticker,
            supply_demand=supply_demand,
            seasonality=seasonality,
            cot=cot,
            valuation_range=valuation_range,
        )
        return BottomUpResult(
            ticker=ticker, asset_class="commodity",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=None, precious_metals=None, bond=None,
            index=None, commodity_deep=commodity_result,
        )

    async def _run_precious_metals(self, metal: str) -> BottomUpResult:
        results = await asyncio.gather(
            self.pm_price_agent.run(metal),
            self.pm_cross_agent.run(),
            self.pm_valuation_agent.run(metal),
            return_exceptions=True,
        )
        price_snap, cross_snap, valuation_snap = [
            r if not isinstance(r, Exception) else default
            for r, default in zip(results, [
                PreciousMetalPriceAgent.default(metal),
                CrossMetalAgent.default(),
                PreciousMetalsValuationAgent.default(),
            ])
        ]
        pm_result = PreciousMetalsResult(
            metal=metal,
            price_analysis=price_snap,
            cross_metal=cross_snap,
            valuation_range=valuation_snap,
            cot_signal=Signal.NEUTRAL,
            currency_impact={},
        )
        return BottomUpResult(
            ticker=metal,
            asset_class="precious_metal",
            fundamentals=None,
            quality=None,
            short_interest=None,
            insider=None,
            earnings_trend=None,
            moat=None,
            valuation_range=valuation_snap,
            precious_metals=pm_result,
            bond=None,
            index=None,
            commodity_deep=None,
        )
