from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import BottomUpResult, FuturesAssessment, RiskAffinity
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.futures_curve import FuturesCurveProvider
from core.ports.llm_provider import LLMProvider
from core.utils.futures_curve import assess_futures_curve


class BottomUpOrchestrator:
    """
    Modus 2 — Bottom-Up Analyse.
    Verzweigt nach underlying (Basiswert-Typ) und delegiert an den zuständigen ChiefAgent.
    """

    def __init__(
        self,
        fundamentals_provider: FundamentalsProvider,
        macro_provider: MacroDataProvider,
        market_provider: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
        futures_curve_provider: "FuturesCurveProvider | None" = None,
    ):
        self.equity_chief          = EquityChiefAgent(fundamentals_provider, market_provider, llm, bus)
        self.bond_chief            = BondChiefAgent(fundamentals_provider, macro_provider, bus)
        self.index_chief           = IndexChiefAgent(market_provider, bus)
        self.commodity_chief       = CommodityChiefAgentMikro(market_provider, bus)
        self.precious_metals_chief = PreciousMetalsChiefAgent(macro_provider, market_provider, bus)
        self.futures_curve_provider = futures_curve_provider

    async def run(
        self,
        ticker: str,
        underlying: Underlying = Underlying.EQUITY,
        wrapper: Wrapper = Wrapper.SINGLE,
        sector: str = "default",
        bond_type: str = "government",
        rate_direction: str = "stable",
        risk_affinity: "RiskAffinity | None" = None,
    ) -> BottomUpResult:
        # Dispatch nach Basiswert-Typ (underlying) — nicht mehr nach Legacy-String.
        # wrapper wird nur an _run_index weitergereicht (SINGLE vs. FUND unterscheidet
        # Direkt-Index von ETF/Fonds-Korb).
        match underlying:
            case Underlying.PRECIOUS_METAL:
                return await self._run_precious_metals(ticker, wrapper)
            case Underlying.BOND:
                return await self._run_bond(ticker, bond_type, rate_direction, risk_affinity)
            case Underlying.EQUITY_INDEX:
                return await self._run_index(ticker, wrapper)
            case Underlying.COMMODITY:
                return await self._run_commodity(ticker, wrapper)
            case _:
                # Default: EQUITY (Einzelaktie)
                return await self._run_equity(ticker, sector)

    async def _run_equity(self, ticker: str, sector: str) -> BottomUpResult:
        try:
            result = await self.equity_chief.run(ticker, sector)
        except Exception:
            result = EquityChiefAgent.default()
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.EQUITY,
            wrapper=Wrapper.SINGLE,
            fundamentals=result.fundamentals,
            quality=result.quality,
            short_interest=result.short_interest,
            insider=result.insider,
            earnings_trend=result.earnings_trend,
            moat=result.moat,
            valuation_range=result.valuation_range,
            precious_metals=None, bond=None, index=None, commodity_deep=None,
            momentum=result.momentum,
        )

    async def _run_bond(self, ticker: str, bond_type: str, rate_direction: str,
                        risk_affinity: "RiskAffinity | None") -> BottomUpResult:
        try:
            bond_result = await self.bond_chief.run(ticker, bond_type, rate_direction, risk_affinity)
        except Exception:
            bond_result = BondChiefAgent.default(ticker, bond_type)
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.BOND,
            wrapper=Wrapper.SINGLE,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=bond_result, index=None, commodity_deep=None,
        )

    async def _run_index(self, ticker: str, wrapper: Wrapper = Wrapper.SINGLE) -> BottomUpResult:
        """Index-Engine: nimmt wrapper entgegen (SINGLE für direkte Indizes, FUND für ETFs).

        Reklassifizierung (Task 2): "etf" landet hier statt im Equity-Zweig — behebt den
        XLE-Durchfall (etf fiel stillschweigend in _run_equity, falsche Analyse-Engine).
        """
        try:
            index_result = await self.index_chief.run(ticker)
        except Exception:
            index_result = IndexChiefAgent.default(ticker)
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.EQUITY_INDEX,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=index_result, commodity_deep=None,
        )

    async def _futures_overlay(self, symbol: str, wrapper: Wrapper) -> "FuturesAssessment | None":
        """Mechanik-Schicht nur bei wrapper=FUTURE (Design §6.5). Defensiv: fehlender Provider
        oder Datenfehler → unavailable statt Crash. Andere Wrapper → None (keine Schicht)."""
        if wrapper != Wrapper.FUTURE:
            return None
        if self.futures_curve_provider is None:
            return FuturesAssessment.unavailable()
        try:
            snap = await self.futures_curve_provider.get_curve(symbol)
        except Exception:
            snap = None
        return assess_futures_curve(snap)

    async def _run_commodity(self, ticker: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            commodity_result = await self.commodity_chief.run(ticker)
        except Exception:
            commodity_result = CommodityChiefAgentMikro.default(ticker)
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.COMMODITY,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=None, commodity_deep=commodity_result,
            futures_curve=await self._futures_overlay(ticker, wrapper),
        )

    async def _run_precious_metals(self, metal: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            pm_result = await self.precious_metals_chief.run(metal)
        except Exception:
            pm_result = PreciousMetalsChiefAgent.default(metal)
        return BottomUpResult(
            ticker=metal,
            underlying=Underlying.PRECIOUS_METAL,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=pm_result.valuation_range,
            precious_metals=pm_result, bond=None, index=None, commodity_deep=None,
            futures_curve=await self._futures_overlay(metal, wrapper),
        )
