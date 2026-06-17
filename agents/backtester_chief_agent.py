import asyncio
from datetime import datetime
from typing import Callable, Optional

from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.bottom_up_backtester_agent import (
    BottomUpBacktesterAgent, _default_benchmark_return, _default_price_on_horizon,
)
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from core.domain.events import BacktesterChiefReady
from core.ports.event_bus import EventBus
from core.ports.memory_port import MemoryPort


class BacktesterChiefAgent:
    def __init__(
        self,
        memory: MemoryPort,
        bus: EventBus,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
    ):
        self.memory = memory
        self.bus    = bus
        self.td_backtester = TopDownBacktesterAgent(memory, benchmark_return=benchmark_return)
        self.bu_backtester = BottomUpBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)
        self.j_backtester  = JudgmentBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)

    def load_context(self) -> dict:
        return self.memory.load_latest_backtester_report("judgment") or {}

    async def run(self) -> None:
        results = await asyncio.gather(
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            return_exceptions=True,
        )
        failures = sum(1 for r in results if isinstance(r, Exception))
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={"failures": failures}))
