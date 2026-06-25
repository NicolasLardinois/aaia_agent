"""Tests fuer die Snapshot-Persistenz des RunManagers.

Hintergrund: `self._latest` (das Domaenen-Ergebnis) liegt nur im Arbeitsspeicher
und ist nach einem Server-Neustart weg -> GET /api/cockpit lieferte dann wieder 204.
Mit injiziertem Snapshot-Store schreibt der RunManager nach jedem erfolgreichen
Lauf das SERIALISIERTE Dict auf Disk und laedt es beim Start; `latest_snapshot()`
liefert das In-Memory-Ergebnis (frisch serialisiert) oder — falls keins da ist —
den persistierten Snapshot.
"""
import asyncio

from fastapi.testclient import TestClient

from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app
from adapters.api.snapshot_store import JsonCockpitSnapshotStore


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


def _run_manager(store=None) -> RunManager:
    return RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster(), snapshot_store=store)


def test_latest_snapshot_is_none_without_store_and_without_run():
    rm = _run_manager()
    assert rm.latest_snapshot() is None


def test_run_persists_serialized_snapshot_to_store(tmp_path):
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    rm = _run_manager(store)
    asyncio.run(rm._execute(_FakeOrch(None), "run-1"))
    persisted = store.load()
    assert persisted is not None
    assert persisted["sources_total"] == 5


def test_fresh_run_manager_loads_persisted_snapshot(tmp_path):
    """Neustart simuliert: ein frischer RunManager hat _latest=None, liefert aber
    den zuvor persistierten Snapshot ueber latest_snapshot()."""
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    store.save({"sources_total": 5, "regime": "Abschwung"})
    rm = _run_manager(store)
    assert rm.latest is None
    assert rm.latest_snapshot() == {"sources_total": 5, "regime": "Abschwung"}


def test_in_memory_result_takes_precedence_over_persisted(tmp_path):
    """Ist ein frisches In-Memory-Ergebnis da, gewinnt es gegenueber dem alten
    Disk-Snapshot (frisch serialisiert)."""
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    store.save({"sources_total": 99, "regime": "veraltet"})
    rm = _run_manager(store)
    asyncio.run(rm._execute(_FakeOrch(None), "run-1"))
    snap = rm.latest_snapshot()
    assert snap["sources_total"] == 5  # aus dem frischen Lauf, nicht die 99


def test_get_cockpit_serves_persisted_snapshot_after_restart(tmp_path):
    """Integrationstest: GET /api/cockpit liefert nach 'Neustart' (frischer
    RunManager mit befuelltem Store) 200 statt 204."""
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    store.save({"sources_total": 5, "regime": "Abschwung"})
    rm = _run_manager(store)
    client = TestClient(create_app(rm))
    r = client.get("/api/cockpit")
    assert r.status_code == 200
    assert r.json()["sources_total"] == 5
