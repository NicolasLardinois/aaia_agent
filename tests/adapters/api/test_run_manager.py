import asyncio
from core.domain.events import MacroChiefReady
from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager


def _default_cockpit() -> CockpitResult:
    return CockpitResult(
        macro=MacroChiefAgent.default(),
        commodities=CommodityChiefAgentMakro.default(),
        sentiment=SentimentChiefAgent.default(),
        yield_curve=YieldCurveChiefAgent.default(),
        sectors=SectorChiefAgent.default(),
    )


class _FakeOrch:
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        return _default_cockpit()


class _RecordingBroadcaster(WebSocketBroadcaster):
    def __init__(self):
        super().__init__()
        self.messages = []
    async def broadcast(self, message):
        self.messages.append(message)


def test_latest_is_none_before_any_run():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    assert rm.latest is None


def test_execute_stores_result_and_broadcasts_terminal_event():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FakeOrch(bus), broadcaster)

    async def scenario():
        await rm._execute(_FakeOrch(bus=None), run_id="run-1")

    asyncio.run(scenario())
    assert rm.latest is not None
    terminal = broadcaster.messages[-1]
    assert terminal["type"] == "CockpitResultReady"
    assert terminal["run_id"] == "run-1"
    assert terminal["payload"]["regime"] == "Abschwung"  # Macro-Default = SLOWDOWN
    assert terminal["payload"]["sources_active"] == 0     # alle Defaults => UNAVAILABLE


def test_sequential_runs_get_distinct_run_ids():
    # Nach dem Lauf-Lock kann nur EIN Lauf gleichzeitig laufen. Zwei NACHEINANDER
    # ausgefuehrte Laeufe (erster abgeschlossen -> Lock frei) muessen verschiedene,
    # nicht-None run_ids liefern (der gleichzeitige Lock-None-Fall ist separat in
    # test_run_lock.py abgedeckt).
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())

    async def scenario():
        a = rm.start_run()
        await asyncio.gather(*list(rm._tasks))  # ersten Lauf abschliessen -> Lock frei
        b = rm.start_run()
        await asyncio.gather(*list(rm._tasks))
        return a, b

    a, b = asyncio.run(scenario())
    assert a is not None and b is not None
    assert a != b
    assert rm.latest is not None


class _FailingOrch:
    """Orchestrator, der mit einer Exception abbricht (Fehlerpfad)."""
    def __init__(self, bus=None):
        self.bus = bus
    async def run(self):
        raise RuntimeError("interner-detail-LEAK-xyz")  # darf NICHT nach aussen gelangen


def test_execute_broadcasts_failure_terminal_on_error():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)
    rm._running = True  # simuliert: start_run() hat den Lock gesetzt

    asyncio.run(rm._execute(_FailingOrch(), run_id="run-err"))

    types = [m["type"] for m in broadcaster.messages]
    assert "CockpitResultReady" not in types          # kein Erfolgs-Terminal
    terminal = broadcaster.messages[-1]
    assert terminal["type"] == "CockpitRunFailed"
    assert terminal["source"] == "run_manager"
    assert terminal["run_id"] == "run-err"
    assert rm._running is False                        # Lock auch im Fehlerfall frei
    assert rm.latest is None                           # kein Ergebnis gespeichert


def test_failure_message_is_generic_and_does_not_leak():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)

    asyncio.run(rm._execute(_FailingOrch(), run_id="run-err"))

    message = broadcaster.messages[-1]["payload"]["message"]
    assert message == "Analyse fehlgeschlagen"
    assert "LEAK" not in message                        # kein Exception-Text nach aussen


def test_failure_path_drains_progress_before_terminal():
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FailingOrch(bus), broadcaster)

    async def scenario():
        async def progress():
            await broadcaster.broadcast({"type": "MacroChiefReady", "source": "m",
                                         "payload": {}, "run_id": "run-err"})
        rm._broadcast_tasks.add(asyncio.create_task(progress()))
        await rm._execute(_FailingOrch(), run_id="run-err")

    asyncio.run(scenario())
    types = [m["type"] for m in broadcaster.messages]
    assert types[-1] == "CockpitRunFailed"
    assert "MacroChiefReady" in types[:-1]              # Fortschritt kam VOR dem Terminal


def test_latest_not_set_when_serialization_fails(monkeypatch):
    # Schlaegt die Serialisierung des Ergebnisses fehl, darf KEIN halbfertiges
    # Ergebnis in latest landen — sonst lieferte ein spaeteres GET /api/cockpit ein
    # Resultat, das der Client nie als "ready" gesehen hat. Erwartet: latest bleibt
    # None, der Client bekommt das terminale CockpitRunFailed.
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _FakeOrch(bus), broadcaster)

    def _boom(_result):
        raise ValueError("serialisierung kaputt")
    monkeypatch.setattr("adapters.api.run_manager.cockpit_to_dict", _boom)

    asyncio.run(rm._execute(_FakeOrch(bus=None), run_id="run-ser"))

    assert rm.latest is None
    types = [m["type"] for m in broadcaster.messages]
    assert "CockpitResultReady" not in types
    assert broadcaster.messages[-1]["type"] == "CockpitRunFailed"


class _ProgressOrch:
    """Orchestrator, der WAEHREND run() ein Fortschritts-Event ueber den Bus meldet
    — wie ein echter Chief-Agent. Genau so fliesst Fortschritt im Produktivpfad:
    bus.publish -> subscribe_all-Handler -> _schedule -> broadcast-Task."""
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        self.bus.publish(MacroChiefReady(source="macro", payload={"k": 1}))
        return _default_cockpit()


def test_success_path_progress_broadcasts_before_terminal():
    # Erfolgspfad-Pendant zu test_failure_path_drains_progress_before_terminal:
    # Vertrag §4 — erst Fortschritt, dann fertig. Anders als der Fehlerpfad-Test
    # wird der Fortschritt hier NICHT von Hand in _broadcast_tasks gelegt, sondern
    # echt ueber den Bus publiziert (start_run() verdrahtet subscribe_all). So ist
    # bewiesen, dass _drain_progress() die ueber den Bus eingespeisten Fortschritts-
    # Broadcasts vor dem terminalen CockpitResultReady zustellt.
    broadcaster = _RecordingBroadcaster()
    rm = RunManager(lambda bus: _ProgressOrch(bus), broadcaster)

    async def scenario():
        rm.start_run()                          # baut Bus + subscribe_all + _execute-Task
        await asyncio.gather(*list(rm._tasks))  # Lauf (inkl. _drain_progress) abschliessen

    asyncio.run(scenario())
    types = [m["type"] for m in broadcaster.messages]
    assert types[-1] == "CockpitResultReady"                     # Terminal kommt ZULETZT
    assert "MacroChiefReady" in types[:-1]                       # Fortschritt davor zugestellt
    assert types.index("MacroChiefReady") < types.index("CockpitResultReady")
