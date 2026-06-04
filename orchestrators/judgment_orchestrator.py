from agents.judgment.judgment_agent import JudgmentAgent
from core.domain.models import BottomUpResult, CockpitResult, DeepDiveResult
from core.domain.top_down_context import derive_top_down_context
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider

FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}


class JudgmentOrchestrator:
    """
    Modus 3 — Kombinations-Urteil.
    Liest CockpitResult (Modus 1) und BottomUpResult (Modus 2) aus dem Cache,
    leitet Top-Down-Kontext ab (pure Funktion, kein API-Call) und ruft
    den JudgmentAgent (LLM) auf.
    """

    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.judgment_agent = JudgmentAgent(llm, bus)

    async def run(
        self,
        cockpit: CockpitResult,
        bottom_up: BottomUpResult,
        market: str,
        in_portfolio: bool = False,
        sector: str = "default",
    ) -> DeepDiveResult:
        top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
        top_down_context   = derive_top_down_context(cockpit, sector=sector) if top_down_available else (
            f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
        )
        return await self.judgment_agent.run(
            ticker=bottom_up.ticker,
            top_down_context=top_down_context,
            bottom_up=bottom_up,
            cockpit=cockpit,
            market=market,
            in_portfolio=in_portfolio,
            top_down_available=top_down_available,
        )
