"""Startet Cockpit-Laeufe als Hintergrund-Task und haelt das letzte Ergebnis.

POST /api/cockpit/run -> start_run() -> str | None.
  - Gibt run_id zurueck, wenn kein Lauf aktiv ist (setzt Lock self._running = True).
  - Gibt None zurueck, wenn bereits ein Lauf laeuft (Route antwortet dann 409).
Fortschritt der Agenten fliesst ueber den Bus (subscribe_all) in den Broadcaster;
nach Abschluss broadcastet der RunManager ein terminales CockpitResultReady mit
dem serialisierten Ergebnis. Der Lock wird in _execute immer im finally freigegeben
(auch bei Fehler), damit kein Stuck-State entsteht.
"""
import asyncio
from typing import Callable
from uuid import uuid4

from adapters.api.cockpit_serializer import cockpit_to_dict
from adapters.api.event_serializer import event_to_dict
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.event_bus.redis_bus import InMemoryEventBus
from core.ports.event_bus import EventBus


class RunManager:
    def __init__(self, orchestrator_factory: Callable[[EventBus], object], broadcaster: WebSocketBroadcaster):
        self._make_orchestrator = orchestrator_factory
        self.broadcaster = broadcaster
        self._latest = None
        self._tasks: set[asyncio.Task] = set()
        self._broadcast_tasks: set[asyncio.Task] = set()
        self._running: bool = False  # Lauf-Lock: True waehrend ein Lauf aktiv ist

    @property
    def latest(self):
        return self._latest

    def start_run(self) -> str | None:
        if self._running:
            return None  # es laeuft bereits ein Lauf -> Route antwortet 409
        self._running = True
        run_id = uuid4().hex
        bus = InMemoryEventBus()
        bus.subscribe_all(lambda ev: self._schedule(event_to_dict(ev, run_id)))
        orchestrator = self._make_orchestrator(bus)
        task = asyncio.create_task(self._execute(orchestrator, run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    def _schedule(self, message: dict) -> None:
        # Sync-Bus-Handler -> async Broadcast: auf demselben Loop, daher create_task.
        # Task-Referenz halten, sonst kann der GC den kurzlebigen Broadcast-Task
        # vor Abschluss einsammeln (CPython-asyncio-Verhalten).
        task = asyncio.create_task(self.broadcaster.broadcast(message))
        self._broadcast_tasks.add(task)
        task.add_done_callback(self._broadcast_tasks.discard)

    async def _execute(self, orchestrator, run_id: str) -> None:
        try:
            result = await orchestrator.run()
            self._latest = result
            # Fortschritts-Broadcasts (fire-and-forget aus dem Bus-Handler) zuerst
            # abschliessen, damit das terminale CockpitResultReady garantiert ZULETZT
            # beim Client ankommt (Vertrag §4: erst Fortschritt, dann fertig).
            if self._broadcast_tasks:
                await asyncio.gather(*self._broadcast_tasks, return_exceptions=True)
            await self.broadcaster.broadcast({
                "type": "CockpitResultReady",
                "source": "run_manager",
                "payload": cockpit_to_dict(result),
                "run_id": run_id,
            })
        finally:
            self._running = False  # Lock immer freigeben (auch nach Fehler)
