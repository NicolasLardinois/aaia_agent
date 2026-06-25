"""
Schweizer Makro-Daten — gemischte Quellen (Hexagonal-Adapter zum SnbDataProvider-Port).

data.snb.ch (CSV-Cube-API):
  - snboffzisa : SNB-Leitzins (Reihe LZ)
  - snbmonagg  : Geldmengen M1/M2/M3 (D0=VV → YoY-Wachstum in %, D1=GM2/GM3)
  - snbbipo    : SNB-Bilanz (D0=T0 → Bilanzsumme, Niveau; Wachstum als YoY berechnet)
  - plkopr     : Landesindex der Konsumentenpreise (D0=VVP → CPI YoY in %)

FRED:
  - CLVMNACSCAB1GQCH : reales BIP (Niveau, quartalsweise) → YoY-Wachstum berechnet
  - IRLTLT01CHM156N  : 10J-Staatsanleihen-Rendite
  - IR3TIB01CHM156N  : 3M-Geldmarktsatz (für 10y-3m-Spread)

Hinweis: Die OECD-MEI-Serien auf FRED (Core-CPI, Arbeitslosigkeit) wurden 2025
eingefroren → bewusst NICHT angebunden. Core-CPI (BFS) / Arbeitslosigkeit (SECO)
folgen in Slice B; bis dahin liefern die Methoden sauber None (UNAVAILABLE).
"""
import csv
import logging
import requests
from typing import Optional

from fredapi import Fred
from core.ports.data_provider import SnbDataProvider

_log = logging.getLogger(__name__)

_SNB_OFFZIS_URL = "https://data.snb.ch/api/cube/snboffzisa/data/csv/en"
_SNB_CUBE_URL = "https://data.snb.ch/api/cube/{cube}/data/csv/en"

# Plausibilitäts-Caps je Kennzahl (Datenrealität, AGENTS.md §3): grobe Garbage-Filter,
# keine fachlichen Schwellen. Inklusive Grenzen.
_CAP_MONEY = (-50.0, 50.0)      # Geldmengen-Jahreswachstum in %
_CAP_BALANCE = (-90.0, 300.0)   # SNB-Bilanz: QE/QT-Sprünge sind real groß
_CAP_CPI = (-10.0, 30.0)        # CH-CPI YoY in %
_CAP_GDP = (-25.0, 25.0)        # reales BIP YoY in %


# ── reine Helfer (data.snb.ch-CSV) ──────────────────────────────────────────
def _parse_snb_csv(text: str) -> list[dict]:
    """Rein: data.snb.ch-CSV → Liste von Zeilen-Dicts.

    Die Cubes haben Vorspann-Zeilen (CubeId, PublishingDate, Leerzeile); die echte
    Kopfzeile beginnt — ohne Anführungszeichen — mit 'Date;'. Funktioniert für 3- und
    4-spaltige Cubes. Fehlt der Header, ist die Liste leer."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.replace('"', "").startswith("Date;"))
    except StopIteration:
        return []
    reader = csv.DictReader(lines[start:], delimiter=";", quotechar='"')
    return [row for row in reader]


def _matches(row: dict, filters: dict) -> bool:
    return all(row.get(k) == v for k, v in filters.items())


def _latest_match(rows: list[dict], filters: dict) -> Optional[tuple[str, float]]:
    """Rein: neueste (date, value)-Zeile, die alle Filter erfüllt und einen
    numerischen Value hat. None bei keinem Treffer."""
    best: Optional[tuple[str, float]] = None
    for row in rows:
        if not _matches(row, filters):
            continue
        date = row.get("Date")
        raw = row.get("Value")
        if not date or raw in (None, ""):
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        if best is None or date > best[0]:
            best = (date, val)
    return best


def _yoy_from_levels(rows: list[dict], filters: dict) -> Optional[float]:
    """Rein: Jahresveränderung in % aus einer Niveau-Reihe (Monatscubes 'YYYY-MM').
    Vergleicht den neuesten Punkt mit demselben Monat des Vorjahres. None, wenn der
    Vorjahrespunkt fehlt oder dort 0 steht (Division)."""
    levels: dict[str, float] = {}
    for row in rows:
        if not _matches(row, filters):
            continue
        date = row.get("Date")
        raw = row.get("Value")
        if not date or raw in (None, ""):
            continue
        try:
            levels[date] = float(raw)
        except ValueError:
            continue
    if not levels:
        return None
    latest = max(levels)
    try:
        year, month = latest.split("-")
        prev_key = f"{int(year) - 1}-{month}"
    except ValueError:
        return None
    prev = levels.get(prev_key)
    if prev in (None, 0) or prev == 0.0:
        return None
    return round((levels[latest] / prev - 1.0) * 100.0, 1)


def _yoy_pct(values: list[float], lag: int) -> Optional[float]:
    """Rein: prozentuale Veränderung des letzten Werts gegenüber 'lag' Schritten zurück.
    None, wenn die Reihe zu kurz ist oder der Basiswert 0 ist."""
    if len(values) <= lag:
        return None
    base = values[-1 - lag]
    if base == 0:
        return None
    return round((values[-1] / base - 1.0) * 100.0, 1)


def _capped(value: Optional[float], cap: tuple[float, float], what: str) -> Optional[float]:
    """Wert nur durchreichen, wenn er im plausiblen Band liegt; sonst WARNING → None."""
    if value is None:
        return None
    lo, hi = cap
    if not (lo <= value <= hi):
        _log.warning("CH-Makro %s: implausibler Wert %s — UNAVAILABLE", what, value)
        return None
    return value


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

    # ── Geldmengen M2/M3 via data.snb.ch (snbmonagg, D0=VV → YoY in %) ────────
    def get_m3_growth(self) -> Optional[float]:
        return self._snb_growth("snbmonagg", {"D0": "VV", "D1": "GM3"}, _CAP_MONEY, "M3")

    def get_m2_growth(self) -> Optional[float]:
        return self._snb_growth("snbmonagg", {"D0": "VV", "D1": "GM2"}, _CAP_MONEY, "M2")

    def _snb_growth(self, cube: str, filters: dict, cap: tuple, what: str) -> Optional[float]:
        """Neuestes YoY-Wachstum (%) aus einem VV-Cube; gerundet, plausibilitätsgedeckelt."""
        rows = self._fetch_snb_cube(cube)
        hit = _latest_match(rows, filters)
        if hit is None:
            return None
        return _capped(round(hit[1], 1), cap, what)

    # ── CPI via data.snb.ch (plkopr, D0=VVP → YoY in %) ──────────────────────
    def get_cpi(self) -> Optional[float]:
        rows = self._fetch_snb_cube("plkopr")
        hit = _latest_match(rows, {"D0": "VVP"})
        if hit is None:
            return None
        return _capped(round(hit[1], 1), _CAP_CPI, "CPI")

    # ── SNB-Bilanzwachstum via data.snb.ch (snbbipo, D0=T0 Niveau → YoY) ──────
    def get_balance_sheet_growth(self) -> Optional[float]:
        rows = self._fetch_snb_cube("snbbipo")
        return _capped(_yoy_from_levels(rows, {"D0": "T0"}), _CAP_BALANCE, "Bilanz")

    # ── BIP-Wachstum via FRED (reales BIP-Niveau, quartalsweise → YoY) ────────
    def get_gdp_growth(self) -> Optional[float]:
        values = self._fred_values("CLVMNACSCAB1GQCH")
        return _capped(_yoy_pct(values, lag=4), _CAP_GDP, "BIP")

    # ── 10J-Staatsanleihen-Rendite via FRED ──────────────────────────────────
    def get_sovereign_yield_10y(self) -> Optional[float]:
        val = self._fetch_series("IRLTLT01CHM156N")
        return round(val, 3) if val is not None else None

    # ── Slice B (noch nicht angebunden) ──────────────────────────────────────
    def get_core_cpi(self) -> Optional[float]:            return None  # TODO Slice B: BFS Kerninflation
    def get_unemployment(self) -> Optional[float]:        return None  # TODO Slice B: SECO/amstat
    def get_sovereign_yield_2y(self) -> Optional[float]:  return None  # keine freie 2J-Quelle

    # ── interne Fetch-Helfer ─────────────────────────────────────────────────
    def _fetch_snb_cube(self, cube: str) -> list[dict]:
        """data.snb.ch-Cube als Zeilen-Dicts; Netz-/Strukturfehler → []."""
        try:
            resp = requests.get(_SNB_CUBE_URL.format(cube=cube), timeout=10)
            resp.raise_for_status()
            return _parse_snb_csv(resp.text)
        except Exception:
            return []

    def _fred_values(self, series_id: str) -> list[float]:
        """FRED-Reihe als float-Liste (älteste zuerst); Fehler → []."""
        try:
            series = self.fred.get_series(series_id).dropna()
            return [float(v) for v in series.tolist()]
        except Exception:
            return []
