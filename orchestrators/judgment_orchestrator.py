from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from agents.judgment.judgment_agent import JudgmentAgent
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
from core.domain.top_down_context import derive_top_down_context
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider
from core.ports.memory_port import MemoryPort

FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}


class JudgmentOrchestrator:
    """
    Modus 3 — Kombinations-Urteil.
    Führt Anomalie-Erkennung durch, lädt Backtester-Kontext,
    ruft JudgmentAgent auf und speichert Ergebnis im Memory.
    """

    def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort):
        self.judgment_agent   = JudgmentAgent(llm, bus)
        self.td_anomaly_agent = TopDownAnomalyAgent()
        self.bu_anomaly_agent = BottomUpAnomalyAgent()
        self.memory           = memory

    async def run(
        self,
        cockpit: CockpitResult,
        bottom_up: BottomUpResult,
        market: str,
        in_portfolio: bool = False,
        sector: str = "default",
    ) -> DeepDiveResult:
        top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
        top_down_context   = (
            derive_top_down_context(cockpit, sector=sector)
            if top_down_available
            else f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
        )

        # History aus Memory für Anomalie-Agenten laden
        ticker_history = self.memory.load_history(bottom_up.ticker, days=90)
        global_history = self.memory.load_global_history(days=90)

        # Anomalie-Erkennung
        td_anomaly = (
            self.td_anomaly_agent.run(cockpit, global_history)
            if cockpit is not None
            else AnomalyReport.empty()
        )
        bu_anomaly = self.bu_anomaly_agent.run(bottom_up, ticker_history)

        # Letzten Judgment-Backtester-Report laden
        backtester_context = self.memory.load_latest_backtester_report("judgment")

        # Urteil generieren
        result = await self.judgment_agent.run(
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

        # Ergebnis in Memory speichern
        self.memory.save_analysis(result, cockpit, price=None)

        return result
