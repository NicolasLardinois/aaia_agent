import json
import math
import os
from datetime import date
from statistics import mean
from typing import Optional

from core.domain.models import MarketRegime

_HISTORY_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", ".cache", "composite_history.json"
)
_MAX_HISTORY = 8

_TREND_NORMAL = 0.05   # Mindestschwelle für einen erkennbaren Trend
_TREND_STRONG = 0.12   # Schwelle für einen deutlichen Trend

# Kalibrierbarer Risk-off-Grenz-Bias: wird vor der Regime-Zuordnung auf den Composite addiert.
# Default 0.0 = heutiges Verhalten. Stufe ②-Kalibrierung schlägt einen Wert vor (kein Auto-Apply).
# b < 0 → Risk-off feuert früher (sensibler); b > 0 → später.
_REGIME_BIAS: float = 0.0


def _score_indicator(key: str, value: float) -> float:
    _yc = lambda v: 1.0 if v > 1 else (0.5 if v > 0 else -1.0)
    rules = {
        "gdp_growth":            lambda v: 1.0 if v > 3 else (0.5 if v > 1 else (-0.5 if v > 0 else -1.0)),
        # Glockenförmig um 2%: Deflation (<1%) UND hohe Inflation (>4%) beide negativ.
        "inflation":             lambda v: (
            0.5 if 1.5 <= v <= 2.5 else
            (-0.5 if (1.0 <= v < 1.5 or 2.5 < v <= 4.0) else -1.0)
        ),
        "unemployment":          lambda v: 1.0 if v < 4 else (0.5 if v < 5 else (-0.5 if v < 7 else -1.0)),
        "fed_rate":              lambda v: 0.5 if v < 2 else (0.0 if v < 4 else (-0.5 if v < 6 else -1.0)),
        "yield_curve":           _yc,   # Fallback-Key (rückwärtskompatibel)
        "consumer_sentiment":    lambda v: 1.0 if v > 90 else (0.5 if v > 70 else (-0.5 if v > 50 else -1.0)),
        "industrial_production": lambda v: 1.0 if v > 3 else (0.5 if v > 0 else (-0.5 if v > -2 else -1.0)),
        "yield_curve_10y3m_usa": _yc,
        "yield_curve_10y2y_eu":  _yc,
        "yield_curve_10y3m_eu":  _yc,
        "yield_curve_10y3m_ch":  _yc,
    }
    return rules.get(key, lambda v: 0.0)(value)


# Gewichte normiert auf Summe 1.0 (Verhältnisse aus ursprünglicher Konfiguration beibehalten).
# yield_curve (10y-2y USA) entfernt — Doppelzählung mit yield_curve_10y3m_usa aufgelöst.
# Bei fehlenden Keys re-normalisiert detect() über weight_total dynamisch.
INDICATOR_WEIGHTS = {
    "gdp_growth":            0.2136752137,
    "unemployment":          0.1709401709,
    "inflation":             0.1282051282,
    "consumer_sentiment":    0.0854700855,
    "industrial_production": 0.0854700855,
    "fed_rate":              0.0427350427,
    "yield_curve_10y3m_usa": 0.1709401710,  # 10Y-3M primär (inkl. ehem. yield_curve-Gewicht)
    "yield_curve_10y2y_eu":  0.0427350427,
    "yield_curve_10y3m_eu":  0.0341880342,
    "yield_curve_10y3m_ch":  0.0256410256,
}


def _load_history() -> list[tuple[str, float]]:
    """Datierte Historie: [(iso_date_str, composite_value), ...] chronologisch."""
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Rückwärtskompatibilität: altes Format war list[float]
        if data and isinstance(data[0], (int, float)):
            return []
        return data
    except Exception:
        return []


def _save_history(history: list[tuple[str, float]], current: float, today: Optional[date] = None) -> None:
    """Speichert max. einen Eintrag pro Tag (überschreibt denselben Tag)."""
    today_str = (today or date.today()).isoformat()
    # Alle Einträge außer dem heutigen behalten; dann heutigen anhängen
    filtered = [(d, v) for d, v in history if d != today_str]
    updated = (filtered + [[today_str, current]])[-_MAX_HISTORY:]
    os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f)


def _trend(history: list[tuple[str, float]], current: float) -> float | None:
    """Positiv = Composite verbessert sich, Negativ = verschlechtert sich.
    Berechnung: current − mean(history) — misst die Abweichung vom Durchschnitt (shift-invariant)."""
    values = [v for _, v in history]
    if len(values) < 2:
        return None
    return current - mean(values)


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
    def detect(self, state: dict, sub_signals: Optional[dict] = None,
               history: Optional[list[tuple[str, float]]] = None) -> tuple[MarketRegime, float, dict]:
        """Returns: (regime, confidence, evidence_per_indicator)
        sub_signals: optionale {key: ±1.0}-Werte (money_supply, credit, labor, buffett)
        mit kleinen Gewichten; fließen in weighted_sum/weight_total ein.
        history: optionale datierte Composite-Reihe [(iso_date, value), ...]. Ist sie
        gesetzt, wird die Cache-Datei WEDER gelesen NOCH geschrieben (Backtest/Replay) —
        der Trend kommt allein aus dieser Reihe.
        """
        evidence = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for key, value in state.items():
            score = _score_indicator(key, value)
            w = INDICATOR_WEIGHTS.get(key, 0.0)
            evidence[key] = round(score, 3)
            weighted_sum += score * w
            weight_total += w

        _SUB_WEIGHT = 0.03
        if sub_signals:
            for sub_key, sub_val in sub_signals.items():
                if sub_val is not None and isinstance(sub_val, (int, float)):
                    evidence[sub_key] = round(sub_val, 3)
                    weighted_sum += sub_val * _SUB_WEIGHT
                    weight_total += _SUB_WEIGHT

        composite = weighted_sum / weight_total if weight_total > 0 else 0.0
        # Reservierter Schlüssel — exakter Composite für Backtest/Trend, kein Indikator-Score.
        # Wird im Replay-Harness direkt ausgelesen statt aus gerundeten evidence-Werten rekonstruiert.
        evidence["composite"] = composite

        if history is None:
            # Live-Pfad: datei-basierte Historie (unverändertes Verhalten)
            loaded = _load_history()
            trend = _trend(loaded, composite)
            _save_history(loaded, composite)
        else:
            # Backtest/Replay-Pfad: rein aus der injizierten Reihe, kein Datei-I/O
            trend = _trend(history, composite)

        evidence["trend"] = trend
        regime     = _regime_from(composite + _REGIME_BIAS, trend)
        confidence = round(min(1.0, abs(composite) * 1.5 + 0.3), 3)
        return regime, confidence, evidence
