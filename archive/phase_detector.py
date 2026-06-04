"""
phase_detector.py — Erweiterung 2: Wirtschaftsphasen-Erkennung
===============================================================
Klassifiziert den aktuellen Wirtschaftszustand in eine von 5 Phasen:
Boom, Aufschwung, Abschwung, Rezession, Erholung
"""


PHASES = ["Boom", "Aufschwung", "Abschwung", "Rezession", "Erholung"]


def _score_indicator(key: str, value: float) -> float:
    """Gibt einen Wert zwischen -1 (schlecht) und +1 (gut) zurück."""
    rules = {
        "gdp_growth":            lambda v: 1.0 if v > 3 else (0.5 if v > 1 else (-0.5 if v > 0 else -1.0)),
        "inflation":             lambda v: 0.5 if 1 < v < 3 else (-0.5 if v > 4 else (-1.0 if v > 6 else 0.0)),
        "unemployment":          lambda v: 1.0 if v < 4 else (0.5 if v < 5 else (-0.5 if v < 7 else -1.0)),
        "fed_rate":              lambda v: 0.5 if v < 2 else (0.0 if v < 4 else (-0.5 if v < 6 else -1.0)),
        "yield_curve":           lambda v: 1.0 if v > 1 else (0.5 if v > 0 else -1.0),
        "consumer_sentiment":    lambda v: 1.0 if v > 90 else (0.5 if v > 70 else (-0.5 if v > 50 else -1.0)),
        "industrial_production": lambda v: 1.0 if v > 3 else (0.5 if v > 0 else (-0.5 if v > -2 else -1.0)),
    }
    return rules.get(key, lambda v: 0.0)(value)


# Phase-Profil: welcher Score-Bereich passt zu welcher Phase
_PHASE_THRESHOLDS = [
    ("Boom",      0.60),
    ("Aufschwung", 0.20),
    ("Erholung",  -0.10),
    ("Abschwung", -0.40),
    ("Rezession", -1.00),
]

INDICATOR_WEIGHTS = {
    "gdp_growth":            0.25,
    "unemployment":          0.20,
    "inflation":             0.15,
    "yield_curve":           0.15,
    "consumer_sentiment":    0.10,
    "industrial_production": 0.10,
    "fed_rate":              0.05,
}


class PhaseDetector:
    def detect(self, state: dict) -> tuple[str, float, dict]:
        """
        Erkennt die Wirtschaftsphase aus dem aktuellen State.

        Returns:
            phase       — Name der erkannten Phase
            confidence  — Konfidenz [0, 1]
            evidence    — Dict mit Score pro Indikator
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

        composite = weighted_sum / weight_total if weight_total > 0 else 0.0

        phase = "Abschwung"
        for name, threshold in _PHASE_THRESHOLDS:
            if composite >= threshold:
                phase = name
                break

        # Konfidenz: wie weit ist composite vom nächsten Schwellenwert entfernt?
        confidence = min(1.0, abs(composite) * 1.5 + 0.3)
        confidence = round(confidence, 3)

        return phase, confidence, evidence
