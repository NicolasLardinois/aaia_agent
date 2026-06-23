import asyncio
import pytest
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager


class _RaisingOrch:
    def __init__(self, bus=None):
        self.bus = bus
    async def run(self):
        raise RuntimeError("Lauf fehlgeschlagen")


def test_start_run_returns_none_when_already_running():
    rm = RunManager(lambda bus: _RaisingOrch(bus), WebSocketBroadcaster())
    rm._running = True  # simuliere aktiven Lauf
    assert rm.start_run() is None


def test_lock_is_released_in_finally_even_on_error():
    rm = RunManager(lambda bus: _RaisingOrch(bus), WebSocketBroadcaster())

    async def scenario():
        rm._running = True
        # _execute faengt den Orchestrator-Fehler intern ab (broadcastet CockpitRunFailed,
        # KEIN Re-Raise) und gibt den Lock im finally trotzdem frei.
        await rm._execute(_RaisingOrch(), "run-x")

    asyncio.run(scenario())
    assert rm._running is False
