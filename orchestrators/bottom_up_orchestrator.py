from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import BottomUpResult
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class BottomUpOrchestrator:
    """
    Modus 2 — Bottom-Up Analyse.
    Verzweigt nach asset_class und delegiert an den zuständigen ChiefAgent.
    """

    def __init__(
        self,
        fundamentals_provider: FundamentalsProvider,
        macro_provider: MacroDataProvider,
        market_provider: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.equity_chief          = EquityChiefAgent(fundamentals_provider, market_provider, llm, bus)
        self.bond_chief            = BondChiefAgent(fundamentals_provider, macro_provider, bus)
        self.index_chief           = IndexChiefAgent(market_provider, bus)
        self.commodity_chief       = CommodityChiefAgentMikro(market_provider, bus)
        self.precious_metals_chief = PreciousMetalsChiefAgent(macro_provider, market_provider, bus)

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
        try:
            result = await self.equity_chief.run(ticker, sector)
        except Exception:
            result = EquityChiefAgent.default()
        return BottomUpResult(
            ticker=ticker, asset_class=asset_class,
            fundamentals=result.fundamentals,
            quality=result.quality,
            short_interest=result.short_interest,
            insider=result.insider,
            earnings_trend=result.earnings_trend,
            moat=result.moat,
            valuation_range=result.valuation_range,
            precious_metals=None, bond=None, index=None, commodity_deep=None,
        )

    async def _run_bond(self, ticker: str, bond_type: str, rate_direction: str) -> BottomUpResult:
        try:
            bond_result = await self.bond_chief.run(ticker, bond_type, rate_direction)
        except Exception:
            bond_result = BondChiefAgent.default(ticker, bond_type)
        return BottomUpResult(
            ticker=ticker, asset_class="bond",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=bond_result, index=None, commodity_deep=None,
        )

    async def _run_index(self, ticker: str) -> BottomUpResult:
        try:
            index_result = await self.index_chief.run(ticker)
        except Exception:
            index_result = IndexChiefAgent.default(ticker)
        return BottomUpResult(
            ticker=ticker, asset_class="index",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=index_result, commodity_deep=None,
        )

    async def _run_commodity(self, ticker: str) -> BottomUpResult:
        try:
            commodity_result = await self.commodity_chief.run(ticker)
        except Exception:
            commodity_result = CommodityChiefAgentMikro.default(ticker)
        return BottomUpResult(
            ticker=ticker, asset_class="commodity",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=None, commodity_deep=commodity_result,
        )

    async def _run_precious_metals(self, metal: str) -> BottomUpResult:
        try:
            pm_result = await self.precious_metals_chief.run(metal)
        except Exception:
            pm_result = PreciousMetalsChiefAgent.default(metal)
        return BottomUpResult(
            ticker=metal, asset_class="precious_metal",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=pm_result.valuation_range,
            precious_metals=pm_result, bond=None, index=None, commodity_deep=None,
        )
