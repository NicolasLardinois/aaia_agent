"""
ECB Statistical Data Warehouse (SDW) adapter.
Fetcht Euro-Area AAA Yield Curve Daten für Spread-Berechnungen.
Alle anderen EcbDataProvider-Methoden bleiben gestubbt bis Eurostat/ECB-SDW vollständig angebunden ist.
"""
import requests
from typing import Optional

from core.ports.data_provider import EcbDataProvider

_BASE = (
    "https://data-api.ecb.europa.eu/service/data/YC/"
    "B.U2.EUR.4F.G_N_A.SV_C_YM.{mat}"
    "?format=jsondata&lastNObservations=1"
)


class EcbSdwProvider(EcbDataProvider):
    """ECB SDW: nur Yield-Spreads implementiert; alle anderen Methoden → None."""

    def get_yield_spreads(self) -> dict[str, float | None]:
        y10 = self._fetch_yield("SR_10Y")
        y2  = self._fetch_yield("SR_2Y")
        y3m = self._fetch_yield("SR_3M")
        spread_10y2y = round(y10 - y2,  3) if y10 is not None and y2  is not None else None
        spread_10y3m = round(y10 - y3m, 3) if y10 is not None and y3m is not None else None
        return {"10y2y": spread_10y2y, "10y3m": spread_10y3m}

    def _fetch_yield(self, maturity: str) -> Optional[float]:
        url = _BASE.format(mat=maturity)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            series = data["dataSets"][0]["series"]
            first_key = next(iter(series))
            observations = series[first_key]["observations"]
            last_key = next(reversed(observations))
            return float(observations[last_key][0])
        except Exception:
            return None

    # ── Stubs ────────────────────────────────────────────────────────────────
    def get_interest_rate(self) -> Optional[float]:         return None
    def get_m3_growth(self) -> Optional[float]:             return None
    def get_balance_sheet_growth(self) -> Optional[float]:  return None
    def get_cpi(self) -> Optional[float]:                   return None
    def get_core_cpi(self) -> Optional[float]:              return None
    def get_ppi(self) -> Optional[float]:                   return None
    def get_gdp_growth(self) -> Optional[float]:            return None
    def get_unemployment(self) -> Optional[float]:          return None
    def get_pmi(self) -> Optional[float]:                   return None
    def get_m2_growth(self) -> Optional[float]:             return None
    def get_sovereign_yields(self) -> dict[str, Optional[float]]:
        return {"DE_10y": None, "IT_10y": None, "FR_10y": None, "ES_10y": None}
