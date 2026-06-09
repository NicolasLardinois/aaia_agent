"""
Schweizer Zinskurven-Spreads via FRED OECD-Serien.
Alle anderen SnbDataProvider-Methoden bleiben gestubbt bis data.snb.ch REST-Zugang verfügbar ist.
"""
from typing import Optional

from fredapi import Fred
from core.ports.data_provider import SnbDataProvider


class FredSnbProvider(SnbDataProvider):
    """FRED OECD-Serien für CH Yield-Spreads; alle anderen Methoden → None."""

    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def get_yield_spreads(self) -> dict[str, float | None]:
        """CH 10y-3m Spread. 2-Jahres-Bond nicht frei verfügbar — 3M SARON als Proxy."""
        rate_10y = self._fetch_series("IRLTLT01CHM156N")
        rate_3m  = self._fetch_series("IR3TIB01CHM156N")
        if rate_10y is None or rate_3m is None:
            return {"10y3m": None}
        return {"10y3m": round(rate_10y - rate_3m, 3)}

    def _fetch_series(self, series_id: str) -> Optional[float]:
        try:
            series = self.fred.get_series(series_id, observation_start="2020-01-01")
            return float(series.dropna().iloc[-1])
        except Exception:
            return None

    # ── Stubs ────────────────────────────────────────────────────────────────
    def get_interest_rate(self) -> Optional[float]:         return None
    def get_m3_growth(self) -> Optional[float]:             return None
    def get_balance_sheet_growth(self) -> Optional[float]:  return None
    def get_cpi(self) -> Optional[float]:                   return None
    def get_core_cpi(self) -> Optional[float]:              return None
    def get_gdp_growth(self) -> Optional[float]:            return None
    def get_unemployment(self) -> Optional[float]:          return None
    def get_m2_growth(self) -> Optional[float]:             return None
    def get_sovereign_yield_10y(self) -> Optional[float]:   return None
    def get_sovereign_yield_2y(self) -> Optional[float]:    return None
