"""Einstiegspunkt der Web-API (uvicorn). Composition Root: verdrahtet die echten
Adapter mit dem TopDownOrchestrator — analog zu app/main.py fuer die CLI.

Start:  python -m app.server      (lauscht auf 127.0.0.1:8000)
"""
import uvicorn

from config.settings import FRED_API_KEY
from adapters.data.fred_api import FredDataProvider
from adapters.data.yahoo_finance import YahooFinanceProvider
from adapters.data.ecb_sdw import EcbSdwProvider
from adapters.data.fred_snb import FredSnbProvider
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app
from orchestrators.top_down_orchestrator import TopDownOrchestrator


def make_orchestrator(bus):
    return TopDownOrchestrator(
        macro=FredDataProvider(FRED_API_KEY),
        ecb=EcbSdwProvider(),
        snb=FredSnbProvider(FRED_API_KEY),
        market=YahooFinanceProvider(),
        bus=bus,
    )


broadcaster = WebSocketBroadcaster()
run_manager = RunManager(make_orchestrator, broadcaster)
app = create_app(run_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
