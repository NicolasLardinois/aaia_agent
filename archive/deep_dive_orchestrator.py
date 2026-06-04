import concurrent.futures

from agents.stock_deep_dive.top_down_context_agent import TopDownContextAgent
from agents.stock_deep_dive.fundamentals_agent import FundamentalsAgent
from agents.stock_deep_dive.short_interest_agent import ShortInterestAgent
from agents.stock_deep_dive.insider_agent import InsiderAgent
from agents.stock_deep_dive.earnings_trend_agent import EarningsTrendAgent
from agents.stock_deep_dive.judgment_agent import JudgmentAgent
from core.domain.models import CockpitResult, DeepDiveResult
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class DeepDiveOrchestrator:
    """
    Führt alle Modus-2-Agenten aus.
    Top-Down aus Cache (CockpitResult), Bottom-Up parallel.
    """

    def __init__(
        self,
        fundamentals_provider: FundamentalsProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.top_down_agent     = TopDownContextAgent(bus)
        self.fundamentals_agent = FundamentalsAgent(fundamentals_provider, bus)
        self.short_agent        = ShortInterestAgent(fundamentals_provider, bus)
        self.insider_agent      = InsiderAgent(fundamentals_provider, bus)
        self.earnings_agent     = EarningsTrendAgent(fundamentals_provider, bus)
        self.judgment_agent     = JudgmentAgent(llm, bus)

    def run(self, ticker: str, cockpit: CockpitResult, sector: str = "default") -> DeepDiveResult:
        top_down_context = self.top_down_agent.run(cockpit, ticker_sector=sector)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            f_fund    = executor.submit(self.fundamentals_agent.run, ticker)
            f_short   = executor.submit(self.short_agent.run, ticker)
            f_insider = executor.submit(self.insider_agent.run, ticker)
            f_earn    = executor.submit(self.earnings_agent.run, ticker)

        return self.judgment_agent.run(
            ticker=ticker,
            top_down_context=top_down_context,
            fundamentals=f_fund.result(),
            short_interest=f_short.result(),
            insider=f_insider.result(),
            earnings_trend=f_earn.result(),
        )
