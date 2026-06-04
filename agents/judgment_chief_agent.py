from agents.judgment.judgment_agent import JudgmentAgent
from core.domain.events import JudgmentChiefReady
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class JudgmentChiefAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.bus = bus
        self.judgment_agent = JudgmentAgent(llm, bus)

    async def run(
        self,
        ticker: str,
        top_down_context: str,
        bottom_up: BottomUpResult,
        cockpit: CockpitResult,
        market: str,
        in_portfolio: bool,
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
            in_portfolio=in_portfolio,
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
