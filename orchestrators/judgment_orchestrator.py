from agents.anomaly_chief_agent import AnomalyChiefAgent
from agents.judgment_chief_agent import JudgmentChiefAgent
from agents.backtester_chief_agent import BacktesterChiefAgent
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
from core.domain.recommendation import FULL_ANALYSIS_MARKETS
from core.domain.top_down_context import derive_top_down_context
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider
from core.ports.memory_port import MemoryPort


class JudgmentOrchestrator:
    """
    Modus 3 — Kombinations-Urteil.
    Koordiniert 3 ChiefAgents: Anomalie-Erkennung, Urteil, Backtesting-Kontext.
    """

    def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort):
        self.memory           = memory
        self.anomaly_chief    = AnomalyChiefAgent(bus)
        self.judgment_chief   = JudgmentChiefAgent(llm, bus)
        self.backtester_chief = BacktesterChiefAgent(memory, bus)

    async def run(
        self,
        cockpit: CockpitResult,
        bottom_up: BottomUpResult,
        market: str,
        in_portfolio: bool = False,
        sector: str = "default",
    ) -> DeepDiveResult:
        top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
        top_down_context = (
            derive_top_down_context(
                cockpit,
                sector=sector,
                market=market,
                asset_class=bottom_up.asset_class,
            )
            if top_down_available
            else f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
        )

        ticker_history = self.memory.load_history(bottom_up.ticker, days=90)
        global_history = self.memory.load_global_history(days=90)

        td_anomaly, bu_anomaly = self.anomaly_chief.run(
            cockpit, bottom_up, ticker_history, global_history, market=market
        )
        backtester_context = self.backtester_chief.load_context()

        try:
            result = await self.judgment_chief.run(
                ticker=bottom_up.ticker,
                top_down_context=top_down_context,
                bottom_up=bottom_up,
                cockpit=cockpit,
                market=market,
                in_portfolio=in_portfolio,
                top_down_available=top_down_available,
                top_down_anomaly=td_anomaly,
                bottom_up_anomaly=bu_anomaly,
                backtester_context=backtester_context,
            )
        except Exception:
            result = JudgmentChiefAgent.default(
                ticker=bottom_up.ticker,
                asset_class=bottom_up.asset_class,
                market=market,
            )

        result.top_down_anomaly = td_anomaly
        result.bottom_up_anomaly = bu_anomaly
        self.memory.save_analysis(result, cockpit, price=None)
        return result
