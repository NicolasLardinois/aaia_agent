"""CNN Fear & Greed Index — echter Daten-Adapter.

Quelle: https://production.dataviz.cnn.io/index/fearandgreed/graphdata/
Liefert den aktuellen Index-Wert 0–100 (0 = Extreme Fear, 100 = Extreme Greed).

Datenrealitaet (bewusst behandelt):
- CNN blockt Anfragen ohne Browser-User-Agent (HTTP 418) → Header gesetzt.
- Der aktuelle Wert liegt verschachtelt unter data["fear_and_greed"]["score"].
- Inoffizieller Endpoint: bei jeder Stoerung → None → Agent liefert UNAVAILABLE.
"""
import logging

import requests

from core.ports.data_provider import SentimentDataProvider

_log = logging.getLogger(__name__)

_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _parse(data: dict) -> float | None:
    """Rein: extrahiert den aktuellen Fear&Greed-Score (0–100) aus dem CNN-JSON.

    Rueckgabe: gerundeter Score, oder None falls die Struktur fehlt, der Wert
    nicht-numerisch ist oder ausserhalb des plausiblen Bereichs [0, 100] liegt
    (Sanity-Cap, AGENTS.md §3 — Einheit ist 0–100, nicht 0–1).
    """
    try:
        score = float(data["fear_and_greed"]["score"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0.0 <= score <= 100.0):
        return None
    return round(score, 1)


class CnnFearGreedProvider(SentimentDataProvider):
    """SentimentDataProvider auf Basis des CNN-Fear-&-Greed-Endpoints."""

    def get_fear_greed(self) -> float | None:
        # Inoffizieller Endpoint → Ausfaelle werden geloggt (WARNING), damit ein
        # dauerhafter Bruch nicht still in UNAVAILABLE verschwindet (Beobachtbarkeit).
        try:
            resp = requests.get(_URL, headers=_HEADERS, timeout=10)
            resp.raise_for_status()
            score = _parse(resp.json())
            if score is None:
                _log.warning(
                    "CNN Fear & Greed: Antwort ohne plausiblen Score "
                    "(Endpoint-Struktur geaendert?) — UNAVAILABLE"
                )
            return score
        except Exception as exc:
            _log.warning("CNN Fear & Greed nicht abrufbar (%s) — UNAVAILABLE", exc)
            return None
