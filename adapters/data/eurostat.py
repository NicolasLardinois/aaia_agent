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


def _parse_jsonstat_latest(data: dict) -> float | None:
    """Rein: juengster befuellter Wert aus dem JSON-stat-value-Objekt.

    value bildet Positions-Index (als String) auf Beobachtung ab; bei single-value-
    Dimensionen entspricht die Position dem Zeit-Index (aelteste=0 … juengste=N).
    Die juengste befuellte Beobachtung ist daher der groesste Integer-Key.
    None bei fehlendem/leerem value oder nicht-numerischem Wert.
    """
    value = data.get("value")
    if not isinstance(value, dict) or not value:
        return None
    try:
        latest_key = max(value, key=int)
        return float(value[latest_key])
    except (ValueError, TypeError):
        return None
