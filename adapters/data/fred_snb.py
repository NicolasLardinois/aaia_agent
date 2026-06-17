"""
Schweizer Zinskurven-Spreads via FRED OECD-Serien.
Leitzins (SNB policy rate, Reihe LZ) via data.snb.ch (Cube snboffzisa, CSV).
Datenquelle: gemischt — FRED für Yields, SNB für Leitzins.
"""
import csv
import requests
from typing import Optional

from fredapi import Fred
from core.ports.data_provider import SnbDataProvider

_SNB_OFFZIS_URL = "https://data.snb.ch/api/cube/snboffzisa/data/csv/en"


class FredSnbProvider(SnbDataProvider):
    """FRED OECD-Serien für CH Yield-Spreads; Leitzins via SNB data.snb.ch; alle anderen Methoden → None."""

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

    # ── SNB-Leitzins via data.snb.ch ─────────────────────────────────────────
    def get_interest_rate(self) -> Optional[float]:
        rows = self._fetch_snb_policy_rate()
        return rows[-1][1] if rows else None

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        from datetime import date
        cutoff = date.today().year - years
        rows = self._fetch_snb_policy_rate()
        return [
            {"date": d, "rate": r} for d, r in rows
            if int(d[:4]) >= cutoff
        ]

    def _fetch_snb_policy_rate(self) -> list:
        """[(iso_date, rate), ...] (aeltester zuerst) der SNB-Reihe LZ aus snboffzisa. Fehler → []."""
        try:
            resp = requests.get(_SNB_OFFZIS_URL, timeout=10)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            start = next(
                i for i, ln in enumerate(lines)
                if ln.replace('"', "").startswith("Date;D0;Value")
            )
            reader = csv.DictReader(lines[start:], delimiter=";", quotechar='"')
            out = []
            for row in reader:
                if row.get("D0") == "LZ":
                    val = row.get("Value")
                    ym = row.get("Date")
                    if val not in (None, "") and ym:
                        out.append((f"{ym}-01", round(float(val), 3)))
            out.sort(key=lambda x: x[0])
            return out
        except Exception:
            return []

    # ── Stubs ────────────────────────────────────────────────────────────────
    def get_m3_growth(self) -> Optional[float]:             return None
    def get_balance_sheet_growth(self) -> Optional[float]:  return None
    def get_cpi(self) -> Optional[float]:                   return None
    def get_core_cpi(self) -> Optional[float]:              return None
    def get_gdp_growth(self) -> Optional[float]:            return None
    def get_unemployment(self) -> Optional[float]:          return None
    def get_m2_growth(self) -> Optional[float]:             return None
    def get_sovereign_yield_10y(self) -> Optional[float]:   return None
    def get_sovereign_yield_2y(self) -> Optional[float]:    return None
