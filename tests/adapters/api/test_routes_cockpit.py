from fastapi.testclient import TestClient
from core.domain.models import CockpitResult
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.events import MacroChiefReady
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app


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
        self.bus.publish(MacroChiefReady(source="macro_chief", payload={}))
        return _default_cockpit()


def _make_client() -> TestClient:
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    return TestClient(create_app(rm))


def test_get_cockpit_is_204_before_any_run():
    client = _make_client()
    r = client.get("/api/cockpit")
    assert r.status_code == 204


def test_post_run_returns_202_and_run_id():
    client = _make_client()
    r = client.post("/api/cockpit/run")
    assert r.status_code == 202
    assert "run_id" in r.json()


def test_ws_streams_until_terminal_then_get_returns_result():
    client = _make_client()
    # `with client:` ist hier PFLICHT (nicht nur Stil): nur als Context-Manager haelt
    # der TestClient EINE langlebige Portal-Event-Loop, die POST und WebSocket teilen.
    # Ohne ihn laeuft jeder HTTP-Request auf einer eigenen, kurzlebigen Loop (Starlette
    # `_portal_factory`), die nach der 202-Antwort abgebaut wird — der von `start_run()`
    # per `asyncio.create_task(_execute)` gestartete Hintergrund-Lauf wird dann u. U.
    # abgebrochen, BEVOR er broadcastet. Die Broadcasts gehen verloren und
    # `ws.receive_json()` blockiert bis zum Timeout (die fruehere flaky CI-Ursache).
    with client:
        with client.websocket_connect("/ws/cockpit") as ws:
            r = client.post("/api/cockpit/run")
            assert r.status_code == 202
            types_seen = []
            terminal = None
            for _ in range(20):  # 1x MacroChiefReady + 1x CockpitResultReady erwartet
                msg = ws.receive_json()
                types_seen.append(msg["type"])
                if msg["type"] == "CockpitResultReady":
                    terminal = msg
                    break
            assert terminal is not None
            assert "MacroChiefReady" in types_seen
            assert types_seen.index("MacroChiefReady") < types_seen.index("CockpitResultReady")
            assert terminal["payload"]["regime"] == "Abschwung"
        g = client.get("/api/cockpit")
        assert g.status_code == 200
        assert g.json()["sources_total"] == 5
