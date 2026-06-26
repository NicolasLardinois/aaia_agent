import asyncio
from datetime import datetime
from typing import Callable, Optional

from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
from agents.backtester.conflict_backtester_agent import ConflictBacktesterAgent
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from agents.backtester.short_backtester_agent import ShortBacktesterAgent
from core.domain.events import BacktesterChiefReady
from core.ports.conflict_store import ConflictStorePort
from core.ports.event_bus import EventBus
from core.ports.memory_port import MemoryPort


class BacktesterChiefAgent:
    def __init__(
        self,
        memory: MemoryPort,
        bus: EventBus,
        price_on_horizon: Optional[Callable[[str, datetime, int], Optional[float]]] = None,
        benchmark_return: Optional[Callable[[str, datetime, int], Optional[float]]] = None,
        conflict_store: Optional[ConflictStorePort] = None,
    ):
        self.memory = memory
        self.bus    = bus
        self.td_backtester = TopDownBacktesterAgent(memory, benchmark_return=benchmark_return)
        self.bu_backtester = BottomUpBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)
        self.j_backtester  = JudgmentBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)
        # Short-Backtester benotet die short_action-Entscheidungen getrennt (Borrow-Kosten,
        # je Grund). Gleiche Provider-Injektion wie die anderen → läuft im selben Lauf mit.
        self.short_backtester = ShortBacktesterAgent(
            memory, price_on_horizon=price_on_horizon, benchmark_return=benchmark_return)
        # Konflikt-Backtester nur, wenn ein Store vorliegt (defensiv: sonst übersprungen).
        # Fehlt der Store → kein Crash, die vier Standard-Backtester laufen unverändert weiter.
        self.conflict_backtester = (
            ConflictBacktesterAgent(conflict_store, memory,
                                    price_on_horizon=price_on_horizon,
                                    benchmark_return=benchmark_return)
            if conflict_store is not None else None
        )

    def load_context(self) -> dict:
        return self.memory.load_latest_backtester_report("judgment") or {}

    async def run(self) -> None:
        tasks = [
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            self.short_backtester.run(),
        ]
        # Konflikt-Backtester bedingt hinzufügen (nur wenn Store vorhanden)
        if self.conflict_backtester is not None:
            tasks.append(self.conflict_backtester.run())
        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = sum(1 for r in results if isinstance(r, Exception))
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={"failures": failures}))
