"""Einstiegspunkt der Web-API (uvicorn). Composition Root: verdrahtet die echten
Adapter mit dem TopDownOrchestrator — analog zu app/main.py fuer die CLI.

Start:  python -m app.server      (lauscht auf 127.0.0.1:8000)
"""
import os
from datetime import date

import uvicorn

from config.settings import FRED_API_KEY, require_keys
from adapters.data.fred_api import FredDataProvider
from adapters.data.world_bank import WorldBankMarketCapProvider
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.eurostat import EurostatEcbProvider
from adapters.data.fred_snb import FredSnbProvider
from adapters.data.cnn_fear_greed import CnnFearGreedProvider
from adapters.data.fmp_metal_spot import FmpMetalSpotProvider
from adapters.data.cboe_put_call import CboePutCallProvider
from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.data.caching_data_provider import wrap_providers
from core.domain.run_context import RunContext
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
# Rohdaten-Snapshot: Skalare in eine eigene DatedHistory-Datei (getrennt von der
# Yield-Spread-Backtest-Historie), Payloads in eine Blob-Datei.
_SNAPSHOT_SCALARS_PATH = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_scalars.json")
_SNAPSHOT_BLOBS_PATH   = os.path.join(os.path.dirname(__file__), "..", ".cache", "snapshot_blobs.json")


def make_orchestrator(bus):
    # Fail-fast beim tatsächlichen Adapter-Aufbau (greift auch auf dem Render-Webserver,
    # der nur das Modul importiert — der __main__-Block läuft dort nie). Modul-Import bleibt
    # dadurch keyfrei (Tests/CI), echte Läufe brechen ohne Pflicht-Keys klar ab.
    require_keys()
    run_ctx = RunContext(as_of=date.today())
    snapshot_store = CompositeSnapshotStore(
        JsonDatedHistory(_SNAPSHOT_SCALARS_PATH), _SNAPSHOT_BLOBS_PATH,
    )
    ecb_cached, market_cached = wrap_providers(
        EurostatEcbProvider(EcbSdwProvider()), YahooFinanceProvider(), run_ctx, snapshot_store,
    )
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=ecb_cached,
        snb=FredSnbProvider(FRED_API_KEY),
        market=market_cached,
        bus=bus,
        sentiment=CnnFearGreedProvider(),
        history=JsonDatedHistory(_HISTORY_PATH),
        world_bank=WorldBankMarketCapProvider(),
        metal_spot=FmpMetalSpotProvider(),
    )


broadcaster = WebSocketBroadcaster()
run_manager = RunManager(make_orchestrator, broadcaster,
                         snapshot_store=JsonCockpitSnapshotStore(_SNAPSHOT_PATH))
app = create_app(run_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
