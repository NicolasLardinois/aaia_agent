import asyncio

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
from agents.stock_deep_dive.equity.quality_agent import QualityAgent
from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent
from agents.stock_deep_dive.equity.insider_agent import InsiderAgent
from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent
from agents.stock_deep_dive.equity.moat_agent import MoatAgent
from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent
from core.domain.events import EquityChiefReady
from core.domain.models import EquityChiefResult
from core.ports.data_provider import FundamentalsProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class EquityChiefAgent:
    def __init__(
        self,
        fundamentals: FundamentalsProvider,
        market: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.fundamentals_agent    = FundamentalsAgent(fundamentals, bus)
        self.quality_agent         = QualityAgent(fundamentals, bus)
        self.short_agent           = ShortInterestAgent(fundamentals, bus)
        self.insider_agent         = InsiderAgent(fundamentals, bus)
        self.earnings_agent        = EarningsTrendAgent(fundamentals, bus)
        self.moat_agent            = MoatAgent(llm, bus)
        self.valuation_range_agent = ValuationRangeAgent(fundamentals, market, bus)

    async def run(self, ticker: str, sector: str = "default") -> EquityChiefResult:
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

        def _safe(r, d): return d if isinstance(r, Exception) else r

        fundamentals    = _safe(results[0], FundamentalsAgent.default())
        quality         = _safe(results[1], QualityAgent.default())
        short_interest  = _safe(results[2], ShortInterestAgent.default())
        insider         = _safe(results[3], InsiderAgent.default())
        earnings_trend  = _safe(results[4], EarningsTrendAgent.default())
        moat            = _safe(results[5], MoatAgent.default())
        valuation_range = _safe(results[6], ValuationRangeAgent.default())

        self.bus.publish(EquityChiefReady(source="equity_chief_agent", payload={"ticker": ticker}))

        return EquityChiefResult(
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=valuation_range,
        )

    @staticmethod
    def default() -> EquityChiefResult:
        return EquityChiefResult(
            fundamentals=FundamentalsAgent.default(),
            quality=QualityAgent.default(),
            short_interest=ShortInterestAgent.default(),
            insider=InsiderAgent.default(),
            earnings_trend=EarningsTrendAgent.default(),
            moat=MoatAgent.default(),
            valuation_range=ValuationRangeAgent.default(),
        )
