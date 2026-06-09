import json
import math
import os
from statistics import mean

from core.domain.models import MarketRegime

_HISTORY_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", ".cache", "composite_history.json"
)
_MAX_HISTORY = 8

_TREND_NORMAL = 0.05   # Mindestschwelle für einen erkennbaren Trend
_TREND_STRONG = 0.12   # Schwelle für einen deutlichen Trend


def _score_indicator(key: str, value: float) -> float:
    _yc = lambda v: 1.0 if v > 1 else (0.5 if v > 0 else -1.0)
    rules = {
        "gdp_growth":            lambda v: 1.0 if v > 3 else (0.5 if v > 1 else (-0.5 if v > 0 else -1.0)),
        "inflation":             lambda v: 0.5 if 1 < v < 3 else (-1.0 if v > 6 else (-0.5 if v > 4 else (-0.25 if v >= 3 else 0.0))),
        "unemployment":          lambda v: 1.0 if v < 4 else (0.5 if v < 5 else (-0.5 if v < 7 else -1.0)),
        "fed_rate":              lambda v: 0.5 if v < 2 else (0.0 if v < 4 else (-0.5 if v < 6 else -1.0)),
        "yield_curve":           _yc,
        "consumer_sentiment":    lambda v: 1.0 if v > 90 else (0.5 if v > 70 else (-0.5 if v > 50 else -1.0)),
        "industrial_production": lambda v: 1.0 if v > 3 else (0.5 if v > 0 else (-0.5 if v > -2 else -1.0)),
        "yield_curve_3m_usa":    _yc,
        "yield_curve_10y2y_eu":  _yc,
        "yield_curve_10y3m_eu":  _yc,
        "yield_curve_10y3m_ch":  _yc,
    }
    return rules.get(key, lambda v: 0.0)(value)


INDICATOR_WEIGHTS = {
    "gdp_growth":            0.25,
    "unemployment":          0.20,
    "inflation":             0.15,
    "yield_curve":           0.12,  # USA 10y-2y
    "consumer_sentiment":    0.10,
    "industrial_production": 0.10,
    "fed_rate":              0.05,
    "yield_curve_3m_usa":    0.08,
    "yield_curve_10y2y_eu":  0.05,
    "yield_curve_10y3m_eu":  0.04,
    "yield_curve_10y3m_ch":  0.03,
}


def _load_history() -> list[float]:
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(history: list[float], current: float) -> None:
    updated = (history + [current])[-_MAX_HISTORY:]
    os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f)


def _trend(history: list[float], current: float) -> float | None:
    """Positiv = Composite verbessert sich, Negativ = verschlechtert sich."""
    if len(history) < 2:
        return None
    return current - mean(history)


def _gauss(x: float, center: float, width: float) -> float:
    """Glockenkurve: 1.0 am Zentrum, fällt symmetrisch ab."""
    return math.exp(-0.5 * ((x - center) / width) ** 2)


def _regime_from(composite: float, trend: float | None) -> MarketRegime:
    """
    Fuzzy-Logik: Jede Phase erhält einen Übereinstimmungswert (Glockenkurve).
    Trend modifiziert diese Werte. Die höchste Punktzahl gewinnt — kein arbiträrer Default.

    Zyklus: DEPRESSION → ERHOLUNG → AUFSCHWUNG → BOOM → ABSCHWUNG → REZESSION → DEPRESSION
    """

    # Basis-Scores: Wie gut passt der aktuelle Composite-Score zu jeder Phase?
    # Zentrum = typischer Composite-Wert dieser Phase; Breite = Toleranzbereich.
    scores: dict[MarketRegime, float] = {
        MarketRegime.DEPRESSION: _gauss(composite, -0.80, 0.15),
        MarketRegime.RECESSION:  _gauss(composite, -0.50, 0.18),
        MarketRegime.SLOWDOWN:   _gauss(composite, -0.10, 0.22),
        MarketRegime.EXPANSION:  _gauss(composite,  0.40, 0.22),
        MarketRegime.BOOM:       _gauss(composite,  0.75, 0.15),
        MarketRegime.RECOVERY:   0.0,  # nur mit bestätigtem Aufwärtstrend möglich
    }

    if trend is None:
        # Noch keine Trendhistorie → reine Niveaueinschätzung
        return max(scores, key=lambda r: scores[r])

    if trend >= _TREND_NORMAL:
        # Aufwärtstrend: ERHOLUNG wird aktiviert, Wachstumsphasen gestärkt
        strength = min(3.0, trend / _TREND_NORMAL)
        scores[MarketRegime.RECOVERY]  = _gauss(composite, -0.30, 0.30) * strength
        scores[MarketRegime.EXPANSION] *= 1.0 + 0.3 * strength
        scores[MarketRegime.RECESSION] *= max(0.3, 1.0 - 0.3 * strength)

    elif trend <= -_TREND_NORMAL:
        # Abwärtstrend: Schwächephasen gestärkt, Wachstumsphasen geschwächt
        strength = min(2.0, abs(trend) / _TREND_STRONG)
        scores[MarketRegime.SLOWDOWN]  *= 1.0 + 0.6 * strength
        scores[MarketRegime.RECESSION] *= 1.0 + 0.4 * strength
        scores[MarketRegime.EXPANSION] *= max(0.2, 1.0 - 0.5 * strength)
        scores[MarketRegime.BOOM]      *= max(0.1, 1.0 - 0.7 * strength)

    # Trend zwischen ±_TREND_NORMAL: zu schwach für Modifikator, RECOVERY bleibt 0.0

    return max(scores, key=lambda r: scores[r])


class RegimeDetector:
    def detect(self, state: dict) -> tuple[MarketRegime, float, dict]:
        """Returns: (regime, confidence, evidence_per_indicator)"""
        evidence = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for key, value in state.items():
            score = _score_indicator(key, value)
            w = INDICATOR_WEIGHTS.get(key, 0.0)
            evidence[key] = round(score, 3)
            weighted_sum += score * w
            weight_total += w

        composite = weighted_sum / weight_total if weight_total > 0 else 0.0

        history = _load_history()
        trend   = _trend(history, composite)
        _save_history(history, composite)

        regime     = _regime_from(composite, trend)
        confidence = round(min(1.0, abs(composite) * 1.5 + 0.3), 3)
        return regime, confidence, evidence
