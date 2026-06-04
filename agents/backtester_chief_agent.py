import asyncio

from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from core.domain.events import BacktesterChiefReady
from core.ports.event_bus import EventBus
from core.ports.memory_port import MemoryPort


class BacktesterChiefAgent:
    def __init__(self, memory: MemoryPort, bus: EventBus):
        self.memory = memory
        self.bus    = bus
        self.td_backtester = TopDownBacktesterAgent(memory)
        self.bu_backtester = BottomUpBacktesterAgent(memory)
        self.j_backtester  = JudgmentBacktesterAgent(memory)

    def load_context(self) -> dict:
        return self.memory.load_latest_backtester_report("judgment") or {}

    async def run(self) -> None:
        await asyncio.gather(
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            return_exceptions=True,
        )
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={}))
