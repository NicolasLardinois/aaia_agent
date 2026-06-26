"""FMP-Adapter für LME-Metall-Spotpreise (Zink/Nickel).

Zink und Nickel handeln an der LME und haben keinen Yahoo-Finance-Ticker; wir
holen ihren letzten Preis über Financial Modeling Prep (FMP). Einziges Stück
echtes I/O — die Schwellen-/Signal-Logik bleibt im Agenten (Hexagonal §1).
"""
import requests

from config.settings import FMP_API_KEY
from core.ports.metal_spot import MetalSpotProvider

_FMP_BASE = "https://financialmodelingprep.com/api/v3"


class FmpMetalSpotProvider(MetalSpotProvider):
    def __init__(self, api_key: str | None = None):
        # Key zentral aus config/settings (nicht os.environ quer im Code), aber
        # für Tests/alternative Quellen explizit überschreibbar.
        self._api_key = FMP_API_KEY if api_key is None else api_key

    def get_spot_price(self, symbol: str) -> float | None:
        if not self._api_key:
            return None  # ohne Key gar nicht erst rufen (Netzwerk-Sparsamkeit/Defensive)
        try:
            resp = requests.get(
                f"{_FMP_BASE}/quote/{symbol}",
                params={"apikey": self._api_key},
                timeout=10,
            )
            data = resp.json()
            if isinstance(data, list) and data:
                return float(data[0]["price"])
            return None
        except Exception:
            return None
