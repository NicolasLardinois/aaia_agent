"""Eurostat-Adapter fuer die EU-Realwirtschaft (HICP, Kern-HICP, PPI, reales BIP,
Arbeitslosenquote) als Decorator ueber EcbDataProvider.

Datenquelle: Eurostat Dissemination API (JSON-stat 2.0), frei, kein API-Key.
Besonderheiten (gegen echte Antworten verifiziert 2026-06-23):
- Mit dem passenden unit-Code liefert Eurostat die Jahresrate DIREKT (kein YoY-Rechnen).
- Die juengste Zeitperiode ist oft noch unveroeffentlicht und fehlt dann im value-Objekt
  (steht in positions-with-no-data) → wir nehmen die juengste BEFUELLTE Beobachtung
  (groesster Integer-Key in value).
- Datasets nutzen unterschiedliche Euroraum-Codes: HICP/PPI/BIP=EA20, Arbeitslosigkeit=EA21.
"""
import logging

import requests

from core.ports.data_provider import EcbDataProvider

_log = logging.getLogger(__name__)

_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# Arbeitslosigkeit (une_rt_m): einzige Quelle der Wahrheit für die Filter-Codes,
# genutzt von get_unemployment (jüngster Wert) UND get_unemployment_history (Reihe).
# Stolperstein: une_rt_m nutzt geo=EA21 (EA20 existiert dort nicht).
_UNE_PARAMS = {"sex": "T", "age": "TOTAL", "unit": "PC_ACT", "s_adj": "SA", "geo": "EA21"}


def _parse_jsonstat_latest(data: dict) -> float | None:
    """Rein: juengster befuellter Wert aus dem JSON-stat-value-Objekt.

    value bildet Positions-Index (als String) auf Beobachtung ab; bei single-value-
    Dimensionen entspricht die Position dem Zeit-Index (aelteste=0 … juengste=N).
    Die juengste befuellte Beobachtung ist daher der groesste Integer-Key.
    None bei fehlendem/leerem value oder nicht-numerischem Wert.
    """
    # Verlaesst sich bewusst auf die sparse-dict-Form von `value` (Position→Wert), die
    # Eurostats Dissemination-API durchgaengig liefert. JSON-stat 2.0 erlaubt theoretisch
    # auch eine dichte Array-Form; die kaeme als list an und faellt hier sicher auf None
    # (→ UNAVAILABLE), nie auf einen falschen Wert.
    value = data.get("value")
    if not isinstance(value, dict) or not value:
        return None
    try:
        latest_key = max(value, key=int)
        return float(value[latest_key])
    except (ValueError, TypeError):
        return None


def _parse_jsonstat_series(data: dict) -> list[float]:
    """Rein: ALLE befüllten Werte aus dem JSON-stat-value-Objekt, ÄLTESTE ZUERST.

    `value` bildet Positions-Index (String) → Beobachtung ab; bei single-value-
    Dimensionen entspricht die Position dem Zeit-Index (älteste=0 … jüngste=N).
    Sortiert daher nach Integer-Key. Nicht-numerische Werte werden übersprungen,
    leeres/fehlendes/nicht-dict `value` → []."""
    value = data.get("value")
    if not isinstance(value, dict) or not value:
        return []
    try:
        keys = sorted(value, key=int)
    except (ValueError, TypeError):
        return []
    out: list[float] = []
    for k in keys:
        try:
            out.append(float(value[k]))
        except (ValueError, TypeError):
            continue
    return out


def _fetch_latest(dataset: str, params: dict, lo: float, hi: float) -> float | None:
    """Eurostat-Abfrage → juengste befuellte Beobachtung, Sanity-Cap [lo, hi], Rundung 1 Stelle.
    Jeder Fehler/Strukturbruch/implausibler Wert → logging.warning → None (Beobachtbarkeit)."""
    full = {"format": "JSON", "lang": "EN", "lastTimePeriod": 6, **params}
    try:
        resp = requests.get(f"{_BASE}/{dataset}", params=full, timeout=10)
        resp.raise_for_status()
        raw = _parse_jsonstat_latest(resp.json())
    except Exception as exc:
        _log.warning("Eurostat %s nicht abrufbar (%s) — UNAVAILABLE", dataset, exc)
        return None
    if raw is None:
        _log.warning("Eurostat %s: keine befuellte Beobachtung (Strukturbruch?) — UNAVAILABLE", dataset)
        return None
    if not (lo <= raw <= hi):
        _log.warning("Eurostat %s: implausibler Wert %s ausserhalb [%s, %s] — UNAVAILABLE",
                     dataset, raw, lo, hi)
        return None
    return round(raw, 1)


class EurostatEcbProvider(EcbDataProvider):
    """EcbDataProvider-Decorator: EU-Realwirtschaft via Eurostat, Rest an base delegiert."""

    def __init__(self, base: EcbDataProvider):
        self._base = base

    # ── Echt via Eurostat (verifizierte Codes, 2026-06-23) ──────────────────
    def get_cpi(self) -> float | None:
        return _fetch_latest("prc_hicp_manr",
                             {"coicop": "CP00", "unit": "RCH_A", "geo": "EA20"}, -50.0, 50.0)

    def get_core_cpi(self) -> float | None:
        return _fetch_latest("prc_hicp_manr",
                             {"coicop": "TOT_X_NRG_FOOD", "unit": "RCH_A", "geo": "EA20"}, -50.0, 50.0)

    def get_ppi(self) -> float | None:
        return _fetch_latest("sts_inppd_m",
                             {"indic_bt": "PRC_PRR_DOM", "nace_r2": "B-E36", "s_adj": "NSA",
                              "unit": "PCH_SM", "geo": "EA20"}, -50.0, 50.0)

    def get_gdp_growth(self) -> float | None:
        return _fetch_latest("namq_10_gdp",
                             {"na_item": "B1GQ", "unit": "CLV_PCH_SM", "s_adj": "SCA",
                              "geo": "EA20"}, -50.0, 50.0)

    def get_unemployment(self) -> float | None:
        return _fetch_latest("une_rt_m", dict(_UNE_PARAMS), 0.0, 100.0)

    def get_unemployment_history(self, months: int = 14) -> list[float]:
        """Monatliche EU-Arbeitslosenquote (%, EA21) der jüngsten `months` Monate,
        ÄLTESTE ZUERST — Datenbasis für die Sahm-Regel im gdp_agent (3M-Schnitt vs.
        12M-Tief). Default 14: deckt das 12M-Tief-Fenster plus den unveröffentlichten
        jüngsten Monat ab. Implausible Werte außerhalb [0,100] werden verworfen;
        jeder Fehler/Strukturbruch → [] (verhaltens-erhaltend → Sahm bleibt None)."""
        full = {"format": "JSON", "lang": "EN", "lastTimePeriod": months, **_UNE_PARAMS}
        try:
            resp = requests.get(f"{_BASE}/une_rt_m", params=full, timeout=10)
            resp.raise_for_status()
            series = _parse_jsonstat_series(resp.json())
        except Exception as exc:
            _log.warning("Eurostat une_rt_m Historie nicht abrufbar (%s) — leer", exc)
            return []
        return [round(v, 1) for v in series if 0.0 <= v <= 100.0]

    # ── Delegation an base (Renditen/Zinsen/Geldmenge/PMI) ──────────────────
    def get_interest_rate(self) -> float | None:
        return self._base.get_interest_rate()

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        return self._base.get_interest_rate_history(years)

    def get_m3_growth(self) -> float | None:
        return self._base.get_m3_growth()

    def get_m2_growth(self) -> float | None:
        return self._base.get_m2_growth()

    def get_balance_sheet_growth(self) -> float | None:
        return self._base.get_balance_sheet_growth()

    def get_pmi(self) -> float | None:
        return self._base.get_pmi()

    def get_sovereign_yields(self) -> dict[str, float | None]:
        return self._base.get_sovereign_yields()

    def get_yield_spreads(self) -> dict[str, float | None]:
        return self._base.get_yield_spreads()

    def get_aaa_10y_yield(self) -> float | None:
        return self._base.get_aaa_10y_yield()
