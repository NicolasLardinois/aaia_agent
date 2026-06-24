"""
ECB Statistical Data Warehouse (SDW) adapter.
Fetcht Euro-Area AAA Yield Curve Daten für Spread-Berechnungen.
Alle anderen EcbDataProvider-Methoden bleiben gestubbt bis Eurostat/ECB-SDW vollständig angebunden ist.
"""
import csv
import logging
import requests
from typing import Optional

from core.ports.data_provider import EcbDataProvider

_log = logging.getLogger(__name__)

_BASE = (
    "https://data-api.ecb.europa.eu/service/data/YC/"
    "B.U2.EUR.4F.G_N_A.SV_C_YM.{mat}"
    "?format=jsondata&lastNObservations=1"
)

_KEYRATE_BASE = (
    "https://data-api.ecb.europa.eu/service/data/FM/"
    "B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata"
)

# Maastricht-Kriterium: 10J Staatsanleihen-Renditen nach Land (IRS-Dataset)
_IRS_BASE = (
    "https://data-api.ecb.europa.eu/service/data/IRS/"
    "M.{country}.L40.CI.0.EUR.N.Z"
    "?format=jsondata&lastNObservations=1"
)

EUROZONE_COUNTRIES = [
    "AT", "BE", "CY", "DE", "EE", "ES", "FI", "FR",
    "GR", "HR", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PT", "SI", "SK",
]

_BSI_BASE = (
    "https://data-api.ecb.europa.eu/service/data/BSI/"
    "M.U2.Y.V.{item}.X.I.U2.2300.Z01.A"
    "?format=jsondata&lastNObservations=1"
)


def _parse_sdmx_last_observation(data: dict) -> float | None:
    """Rein: letzter Beobachtungswert aus ECB-SDMX-JSON
    (data["dataSets"][0]["series"][<key>]["observations"][<key>][0]).
    None bei fehlender Struktur, leerer Reihe oder nicht-numerischem Wert."""
    try:
        series = data["dataSets"][0]["series"]
        first_key = next(iter(series))
        observations = series[first_key]["observations"]
        last_key = next(reversed(observations))
        return float(observations[last_key][0])
    except (KeyError, IndexError, TypeError, ValueError, StopIteration):
        return None


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
        try:
            response = requests.get(_BASE.format(mat=maturity), timeout=10)
            response.raise_for_status()
            return _parse_sdmx_last_observation(response.json())
        except Exception:
            return None

    def get_interest_rate(self) -> Optional[float]:
        rows = self._fetch_keyrate_rows(self._KEYRATE_URL("&lastNObservations=1"))
        return rows[-1][1] if rows else None

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        from datetime import date
        start = f"{date.today().year - years}-01-01"
        rows = self._fetch_keyrate_rows(self._KEYRATE_URL(f"&startPeriod={start}"))
        return [{"date": d, "rate": r} for d, r in rows]

    @staticmethod
    def _KEYRATE_URL(suffix: str) -> str:
        return _KEYRATE_BASE + suffix

    def _fetch_keyrate_rows(self, url: str) -> list:
        """[(date_str, rate_float), ...] (aeltester zuerst) aus ECB-csvdata. Fehler → []."""
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            reader = csv.DictReader(resp.text.splitlines())
            out = []
            for row in reader:
                d = row.get("TIME_PERIOD")
                v = row.get("OBS_VALUE")
                if d and v not in (None, ""):
                    out.append((d, round(float(v), 3)))
            out.sort(key=lambda x: x[0])
            return out
        except Exception:
            return []

    def _fetch_bsi_growth(self, item: str) -> float | None:
        """ECB-SDW BSI-Jahreswachstum (M30/M20) in %. Sanity-Cap -50..50, Rundung 1 Stelle;
        Fehler/Strukturbruch/implausibel → logging.warning → None (Beobachtbarkeit)."""
        try:
            response = requests.get(_BSI_BASE.format(item=item), timeout=10)
            response.raise_for_status()
            raw = _parse_sdmx_last_observation(response.json())
        except Exception as exc:
            _log.warning("ECB SDW BSI %s nicht abrufbar (%s) — UNAVAILABLE", item, exc)
            return None
        if raw is None:
            _log.warning("ECB SDW BSI %s: keine Beobachtung (Strukturbruch?) — UNAVAILABLE", item)
            return None
        if not (-50.0 <= raw <= 50.0):
            _log.warning("ECB SDW BSI %s: implausibler Wert %s — UNAVAILABLE", item, raw)
            return None
        return round(raw, 1)

    # ── Stubs ────────────────────────────────────────────────────────────────
    def get_m3_growth(self) -> float | None:
        return self._fetch_bsi_growth("M30")

    def get_balance_sheet_growth(self) -> Optional[float]:  return None
    def get_cpi(self) -> Optional[float]:                   return None
    def get_core_cpi(self) -> Optional[float]:              return None
    def get_ppi(self) -> Optional[float]:                   return None
    def get_gdp_growth(self) -> Optional[float]:            return None
    def get_unemployment(self) -> Optional[float]:          return None
    def get_pmi(self) -> Optional[float]:                   return None

    def get_m2_growth(self) -> float | None:
        return self._fetch_bsi_growth("M20")
    def get_sovereign_yields(self) -> dict[str, Optional[float]]:
        return {f"{c}_10y": self._fetch_country_yield(c) for c in EUROZONE_COUNTRIES}

    def _fetch_country_yield(self, country: str) -> Optional[float]:
        try:
            response = requests.get(_IRS_BASE.format(country=country), timeout=10)
            response.raise_for_status()
            return _parse_sdmx_last_observation(response.json())
        except Exception:
            return None
