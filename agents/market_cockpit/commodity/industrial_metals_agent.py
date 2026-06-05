import asyncio
import os

import requests

from core.domain.events import IndustrialMetalsDataReady
from core.domain.models import IndustrialMetalsSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

# Kupfer und Aluminium: CME-Futures, verfügbar über Yahoo Finance
TICKERS = {"copper": "HG=F", "aluminium": "ALI=F"}
# Zink und Nickel handeln an der LME — kein Yahoo Finance Ticker. Wir holen sie via FMP.
_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _fmp_price(symbol: str) -> float | None:
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{_FMP_BASE}/quote/{symbol}",
            params={"apikey": api_key},
            timeout=10,
        )
        data = resp.json()
        if isinstance(data, list) and data:
            return float(data[0]["price"])
        return None
    except Exception:
        return None


_DEFAULT = IndustrialMetalsSnapshot(
    copper_usd=None, aluminium_usd=None, zinc_usd=None, nickel_usd=None, signal=Signal.NEUTRAL,
)

# Kupfer ist "Dr. Copper" — stärkster Frühindikator für Wirtschaftsaktivität
def _signal(copper: float | None) -> Signal:
    if copper is None:
        return Signal.NEUTRAL
    # Grobe Orientierungswerte (USD/lb)
    if copper > 4.5:
        return Signal.BULLISH   # hohe Industrienachfrage
    if copper < 3.0:
        return Signal.BEARISH   # schwache Nachfrage
    return Signal.NEUTRAL


class IndustrialMetalsAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> IndustrialMetalsSnapshot:
        copper, alu, zinc, nickel = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, TICKERS["copper"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["aluminium"]),
            asyncio.to_thread(_fmp_price, "ZINC"),
            asyncio.to_thread(_fmp_price, "NICKEL"),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        copper = _safe(copper); alu = _safe(alu); zinc = _safe(zinc); nickel = _safe(nickel)

        result = IndustrialMetalsSnapshot(
            copper_usd=copper, aluminium_usd=alu, zinc_usd=zinc, nickel_usd=nickel,
            signal=_signal(copper),
        )
        self.bus.publish(IndustrialMetalsDataReady(source="industrial_metals_agent", payload={
            "copper": copper, "aluminium": alu, "zinc": zinc, "nickel": nickel,
        }))
        return result

    @staticmethod
    def default() -> IndustrialMetalsSnapshot:
        return _DEFAULT
