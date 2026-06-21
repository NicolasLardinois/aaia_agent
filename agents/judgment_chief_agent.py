from agents.judgment.judgment_agent import JudgmentAgent
from core.domain.events import JudgmentChiefReady
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult, InvestmentRecommendation, PositionState, Recommendation
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class JudgmentChiefAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus, portfolio_port=None):
        self.bus = bus
        self.judgment_agent = JudgmentAgent(llm, bus, portfolio_port)

    async def run(
        self,
        ticker: str,
        top_down_context: str,
        bottom_up: BottomUpResult,
        cockpit: CockpitResult,
        market: str,
        current_position: PositionState,
        top_down_available: bool,
        top_down_anomaly: AnomalyReport,
        bottom_up_anomaly: AnomalyReport,
        backtester_context: dict,
    ) -> DeepDiveResult:
        result = await self.judgment_agent.run(
            ticker=ticker,
            top_down_context=top_down_context,
            bottom_up=bottom_up,
            cockpit=cockpit,
            market=market,
            current_position=current_position,
            top_down_available=top_down_available,
            top_down_anomaly=top_down_anomaly,
            bottom_up_anomaly=bottom_up_anomaly,
            backtester_context=backtester_context,
        )

        self.bus.publish(JudgmentChiefReady(source="judgment_chief_agent", payload={
            "ticker": ticker,
            "recommendation": result.recommendation.action.value,
            "confidence": result.confidence,
        }))

        return result

    @staticmethod
    def default(ticker: str = "", asset_class: str = "equity", market: str = "unknown") -> DeepDiveResult:
        return DeepDiveResult(
            ticker=ticker,
            asset_class=asset_class,
            market=market,
            top_down_context="Nicht verfügbar.",
            top_down_available=False,
            judgment="Urteil nicht verfügbar.",
            alignment="mixed",
            recommendation=InvestmentRecommendation(
                action=Recommendation.HOLD,
                short_type=None,
                short_warning=None,
                confidence=0.0,
                reasoning="Urteil fehlgeschlagen.",
            ),
            dominant_signal="neutral",
            confidence=0.0,
            xai_explanation="",
        )
