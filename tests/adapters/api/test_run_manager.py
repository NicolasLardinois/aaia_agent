import asyncio
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


def test_start_run_returns_distinct_run_ids():
    rm = RunManager(lambda bus: _FakeOrch(bus), WebSocketBroadcaster())

    async def scenario():
        a = rm.start_run()
        b = rm.start_run()
        await asyncio.gather(*list(rm._tasks))
        return a, b

    a, b = asyncio.run(scenario())
    assert a != b
    assert rm.latest is not None
