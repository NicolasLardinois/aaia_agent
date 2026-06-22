import pytest
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


class _FakeOrch:
    def __init__(self, bus):
        self.bus = bus
    async def run(self):
        return CockpitResult(
            macro=MacroChiefAgent.default(), commodities=CommodityChiefAgentMakro.default(),
            sentiment=SentimentChiefAgent.default(), yield_curve=YieldCurveChiefAgent.default(),
            sectors=SectorChiefAgent.default(),
        )


def _client():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())
    return TestClient(create_app(rm))


def test_get_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    assert client.get("/api/cockpit").status_code == 401
    assert client.get("/api/cockpit", headers={"Authorization": "Bearer falsch"}).status_code == 401
    # korrektes Token -> kein 401 (204, da noch kein Lauf)
    assert client.get("/api/cockpit", headers={"Authorization": "Bearer geheim"}).status_code == 204


def test_post_requires_token_when_set(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    assert client.post("/api/cockpit/run").status_code == 401
    assert client.post("/api/cockpit/run", headers={"Authorization": "Bearer falsch"}).status_code == 401
    assert client.post("/api/cockpit/run", headers={"Authorization": "Bearer geheim"}).status_code == 202


def test_ws_rejects_without_token(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/cockpit"):
            pass  # ohne ?token -> Verbindung wird abgewiesen


def test_ws_accepts_with_token(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    client = _client()
    with client.websocket_connect("/ws/cockpit?token=geheim") as ws:
        assert ws is not None  # akzeptiert
