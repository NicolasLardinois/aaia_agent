import asyncio

from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from agents.stock_deep_dive.bond.bond_credit_agent import BondCreditAgent
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent
from core.domain.events import BondChiefReady
from core.domain.models import BondResult
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
from core.ports.event_bus import EventBus


class BondChiefAgent:
    def __init__(
        self,
        fundamentals: FundamentalsProvider,
        macro: MacroDataProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.bond_metrics_agent  = BondMetricsAgent(fundamentals, macro, bus)
        self.bond_duration_agent = BondDurationAgent(fundamentals, bus)
        self.bond_credit_agent   = BondCreditAgent(fundamentals, bus)
        self.bond_spread_agent   = BondSpreadAgent(fundamentals, bus)

    async def run(self, ticker: str, bond_type: str, rate_direction: str) -> BondResult:
        results = await asyncio.gather(
            self.bond_metrics_agent.run(ticker, bond_type),
            self.bond_duration_agent.run(ticker, rate_direction),
            self.bond_credit_agent.run(ticker),
            self.bond_spread_agent.run(ticker),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        metrics  = _safe(results[0], BondMetricsAgent.default())
        duration = _safe(results[1], BondDurationAgent.default())
        credit   = _safe(results[2], BondCreditAgent.default())
        spread   = _safe(results[3], BondSpreadAgent.default())

        self.bus.publish(BondChiefReady(source="bond_chief_agent", payload={"ticker": ticker}))

        return BondResult(ticker=ticker, bond_type=bond_type, metrics=metrics, duration=duration, credit=credit, spread=spread)

    @staticmethod
    def default(ticker: str = "", bond_type: str = "government") -> BondResult:
        return BondResult(
            ticker=ticker, bond_type=bond_type,
            metrics=BondMetricsAgent.default(),
            duration=BondDurationAgent.default(),
            credit=BondCreditAgent.default(),
            spread=BondSpreadAgent.default(),
        )
