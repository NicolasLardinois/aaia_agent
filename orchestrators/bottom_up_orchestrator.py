from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.commodity_chief_agent_mikro import CommodityChiefAgentMikro
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import BottomUpResult, FundInfo, FuturesAssessment, FuturesShortAssessment, RiskAffinity
from core.domain.taxonomy import Underlying, Wrapper
from core.ports.cost_floor import CostFloorProvider
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.fund_info import FundInfoProvider
from core.ports.futures_curve import FuturesCurveProvider
from core.ports.llm_provider import LLMProvider
from core.utils.futures_curve import assess_futures_curve
from core.utils.futures_short import assess_futures_short


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
        fund_info_provider: "FundInfoProvider | None" = None,
        futures_curve_provider: "FuturesCurveProvider | None" = None,
        cost_floor_provider: "CostFloorProvider | None" = None,
        cot_provider: "COTProvider | None" = None,
        cape_provider: "ShillerCapeProvider | None" = None,
    ):
        self.equity_chief          = EquityChiefAgent(fundamentals_provider, market_provider, llm, bus)
        self.bond_chief            = BondChiefAgent(fundamentals_provider, macro_provider, bus)
        self.index_chief           = IndexChiefAgent(market_provider, bus, cape_provider=cape_provider)
        self.commodity_chief       = CommodityChiefAgentMikro(market_provider, bus, cot_provider=cot_provider)
        self.precious_metals_chief = PreciousMetalsChiefAgent(macro_provider, market_provider, bus, cot_provider=cot_provider)
        self.fund_info_provider     = fund_info_provider
        self.futures_curve_provider = futures_curve_provider
        self.cost_floor_provider    = cost_floor_provider

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
        # Dispatch nach Basiswert-Typ (underlying). wrapper geht an die Pfade, die ihn
        # auswerten (_run_index, _run_commodity, _run_precious_metals); danach wird die
        # Fund-Info-Schicht zentral über jedes Ergebnis gelegt. Die Futures-Mechanik-Schicht
        # bleibt pfadlokal (Commodity/Edelmetall, Phase 2a).
        match underlying:
            case Underlying.PRECIOUS_METAL:
                result = await self._run_precious_metals(ticker, wrapper)
            case Underlying.BOND:
                result = await self._run_bond(ticker, bond_type, rate_direction, risk_affinity)
            case Underlying.EQUITY_INDEX:
                result = await self._run_index(ticker, wrapper)
            case Underlying.COMMODITY:
                result = await self._run_commodity(ticker, wrapper)
            case _:
                # Default: EQUITY (Einzelaktie)
                result = await self._run_equity(ticker, sector)

        # Fund-Info-Schicht (§6.6): hängt am WRAPPER, nicht am Basiswert. Jeder ETF/Fonds
        # bekommt sie — Aktien-Index-ETF ebenso wie Anleihe-, Rohstoff- oder Edelmetall-ETF
        # (z. B. GLD). Andere Wrapper → None (keine Schicht).
        fund = await self._fund_overlay(ticker, wrapper)
        if fund is not None:
            result.fund_info = fund
        return result

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

    async def _fund_overlay(self, symbol: str, wrapper: Wrapper) -> "FundInfo | None":
        """Info-Schicht nur bei wrapper=FUND (Design §6.6). Defensiv: fehlender Provider
        oder Datenfehler → unavailable statt Crash. Andere Wrapper → None (keine Schicht)."""
        if wrapper != Wrapper.FUND:
            return None
        if self.fund_info_provider is None:
            return FundInfo.unavailable()
        try:
            info = await self.fund_info_provider.get_fund_info(symbol)
        except Exception:
            info = None
        return info if info is not None else FundInfo.unavailable()

    async def _fetch_curve_snap(self, symbol: str, wrapper: Wrapper):
        """Holt die Terminkurve EINMAL (defensiv). None bei Nicht-Future/fehlendem Provider/Fehler.
        Long- und Short-Overlay teilen sich dieses Ergebnis (kein Doppel-Fetch)."""
        if wrapper != Wrapper.FUTURE or self.futures_curve_provider is None:
            return None
        try:
            return await self.futures_curve_provider.get_curve(symbol)
        except Exception:
            return None

    def _futures_long_overlay(self, snap, wrapper: Wrapper) -> "FuturesAssessment | None":
        """Long-Mechanik (Phase 2a) aus dem bereits geholten Snapshot. wrapper≠FUTURE → None;
        Future ohne Daten → unavailable() (via assess_futures_curve(None))."""
        if wrapper != Wrapper.FUTURE:
            return None
        return assess_futures_curve(snap)

    async def _futures_short_overlay(self, snap, symbol: str, underlying: Underlying,
                                     wrapper: Wrapper) -> "FuturesShortAssessment | None":
        """Short-Mechanik (Phase 3) nur bei wrapper=FUTURE & Rohstoff/Edelmetall. Kostenboden
        defensiv: fehlender Provider/Exception → floor=None (Deckel via floor_applied=False)."""
        if wrapper != Wrapper.FUTURE or underlying not in (Underlying.COMMODITY, Underlying.PRECIOUS_METAL):
            return None
        floor = None
        if self.cost_floor_provider is not None:
            try:
                floor = await self.cost_floor_provider.get_cost_floor(underlying, symbol)
            except Exception:
                floor = None
        return assess_futures_short(snap, floor)

    async def _run_commodity(self, ticker: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            commodity_result = await self.commodity_chief.run(ticker)
        except Exception:
            commodity_result = CommodityChiefAgentMikro.default(ticker)
        snap = await self._fetch_curve_snap(ticker, wrapper)
        return BottomUpResult(
            ticker=ticker,
            underlying=Underlying.COMMODITY,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=None, commodity_deep=commodity_result,
            futures_curve=self._futures_long_overlay(snap, wrapper),
            futures_short=await self._futures_short_overlay(snap, ticker, Underlying.COMMODITY, wrapper),
        )

    async def _run_precious_metals(self, metal: str, wrapper: Wrapper = Wrapper.FUTURE) -> BottomUpResult:
        try:
            pm_result = await self.precious_metals_chief.run(metal)
        except Exception:
            pm_result = PreciousMetalsChiefAgent.default(metal)
        snap = await self._fetch_curve_snap(metal, wrapper)
        return BottomUpResult(
            ticker=metal,
            underlying=Underlying.PRECIOUS_METAL,
            wrapper=wrapper,
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=pm_result.valuation_range,
            precious_metals=pm_result, bond=None, index=None, commodity_deep=None,
            futures_curve=self._futures_long_overlay(snap, wrapper),
            futures_short=await self._futures_short_overlay(snap, metal, Underlying.PRECIOUS_METAL, wrapper),
        )
