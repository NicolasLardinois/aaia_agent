"""Einstiegspunkt der Web-API (uvicorn). Composition Root: verdrahtet die echten
Adapter mit dem TopDownOrchestrator — analog zu app/main.py fuer die CLI.

Start:  python -m app.server      (lauscht auf 127.0.0.1:8000)
"""
import os

import uvicorn

from config.settings import FRED_API_KEY
from adapters.data.fred_api import FredDataProvider
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.eurostat import EurostatEcbProvider
from adapters.data.fred_snb import FredSnbProvider
from adapters.data.cnn_fear_greed import CnnFearGreedProvider
from adapters.persistence.json_dated_history import JsonDatedHistory
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.snapshot_store import JsonCockpitSnapshotStore
from adapters.api.app_factory import create_app
from orchestrators.top_down_orchestrator import TopDownOrchestrator

# Persistente 10Y-3M-Historie für das Yield-Curve-Bull-Steepening-Signal (über Läufe hinweg).
_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", ".cache", "yield_spread_history.json")
# Persistenter Snapshot des letzten Cockpit-Ergebnisses, damit GET /api/cockpit
# auch direkt nach einem Server-Neustart ein Ergebnis liefert (statt 204).
_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "..", ".cache", "cockpit_snapshot.json")


def make_orchestrator(bus):
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=EurostatEcbProvider(EcbSdwProvider()),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
        sentiment=CnnFearGreedProvider(),
        history=JsonDatedHistory(_HISTORY_PATH),
    )


broadcaster = WebSocketBroadcaster()
run_manager = RunManager(make_orchestrator, broadcaster,
                         snapshot_store=JsonCockpitSnapshotStore(_SNAPSHOT_PATH))
app = create_app(run_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
