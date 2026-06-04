"""
weights.py — Erweiterung 3: Dynamische Phasen-Gewichte & Nutzenfunktion
========================================================================
Definiert portfoliospezifische Gewichte pro Wirtschaftsphase und berechnet
den Utility-Score für jedes Portfolio (Aktien, Anleihen, Cash, Gold).
"""

# PHASE_WEIGHTS[phase][portfolio][indicator] = Gewicht
PHASE_WEIGHTS: dict[str, dict[str, dict[str, float]]] = {
    "Boom": {
        "Aktien":   {"gdp_growth": 0.35, "consumer_sentiment": 0.25, "industrial_production": 0.20, "unemployment": 0.10, "inflation": 0.05, "yield_curve": 0.03, "fed_rate": 0.02},
        "Anleihen": {"fed_rate": 0.35, "yield_curve": 0.30, "inflation": 0.20, "gdp_growth": 0.08, "unemployment": 0.04, "consumer_sentiment": 0.02, "industrial_production": 0.01},
        "Cash":     {"inflation": 0.40, "fed_rate": 0.30, "unemployment": 0.15, "yield_curve": 0.10, "gdp_growth": 0.03, "consumer_sentiment": 0.01, "industrial_production": 0.01},
        "Gold":     {"inflation": 0.35, "yield_curve": 0.25, "fed_rate": 0.20, "unemployment": 0.10, "gdp_growth": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
    },
    "Aufschwung": {
        "Aktien":   {"gdp_growth": 0.30, "industrial_production": 0.25, "consumer_sentiment": 0.20, "unemployment": 0.15, "inflation": 0.05, "yield_curve": 0.03, "fed_rate": 0.02},
        "Anleihen": {"fed_rate": 0.30, "yield_curve": 0.25, "inflation": 0.25, "gdp_growth": 0.10, "unemployment": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Cash":     {"inflation": 0.35, "fed_rate": 0.30, "unemployment": 0.20, "yield_curve": 0.10, "gdp_growth": 0.03, "consumer_sentiment": 0.01, "industrial_production": 0.01},
        "Gold":     {"inflation": 0.30, "yield_curve": 0.25, "fed_rate": 0.20, "unemployment": 0.15, "gdp_growth": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
    },
    "Abschwung": {
        "Aktien":   {"gdp_growth": 0.20, "consumer_sentiment": 0.20, "industrial_production": 0.20, "unemployment": 0.20, "inflation": 0.10, "yield_curve": 0.05, "fed_rate": 0.05},
        "Anleihen": {"yield_curve": 0.35, "fed_rate": 0.25, "inflation": 0.20, "gdp_growth": 0.08, "unemployment": 0.07, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Cash":     {"inflation": 0.30, "fed_rate": 0.30, "unemployment": 0.20, "yield_curve": 0.10, "gdp_growth": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Gold":     {"yield_curve": 0.30, "inflation": 0.30, "fed_rate": 0.15, "unemployment": 0.12, "gdp_growth": 0.05, "consumer_sentiment": 0.05, "industrial_production": 0.03},
    },
    "Rezession": {
        "Aktien":   {"gdp_growth": 0.20, "unemployment": 0.25, "consumer_sentiment": 0.20, "industrial_production": 0.20, "inflation": 0.08, "yield_curve": 0.05, "fed_rate": 0.02},
        "Anleihen": {"yield_curve": 0.40, "fed_rate": 0.25, "inflation": 0.15, "gdp_growth": 0.08, "unemployment": 0.07, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Cash":     {"unemployment": 0.30, "fed_rate": 0.25, "inflation": 0.20, "yield_curve": 0.12, "gdp_growth": 0.05, "consumer_sentiment": 0.05, "industrial_production": 0.03},
        "Gold":     {"yield_curve": 0.35, "inflation": 0.30, "unemployment": 0.15, "fed_rate": 0.10, "gdp_growth": 0.04, "consumer_sentiment": 0.04, "industrial_production": 0.02},
    },
    "Erholung": {
        "Aktien":   {"gdp_growth": 0.28, "consumer_sentiment": 0.22, "industrial_production": 0.22, "unemployment": 0.15, "inflation": 0.07, "yield_curve": 0.04, "fed_rate": 0.02},
        "Anleihen": {"fed_rate": 0.30, "yield_curve": 0.28, "inflation": 0.22, "gdp_growth": 0.10, "unemployment": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Cash":     {"inflation": 0.32, "fed_rate": 0.28, "unemployment": 0.20, "yield_curve": 0.10, "gdp_growth": 0.05, "consumer_sentiment": 0.03, "industrial_production": 0.02},
        "Gold":     {"inflation": 0.32, "yield_curve": 0.28, "fed_rate": 0.18, "unemployment": 0.10, "gdp_growth": 0.05, "consumer_sentiment": 0.05, "industrial_production": 0.02},
    },
}

# Normierte Score-Funktionen pro Indikator [-1, +1]
def _normalize(key: str, value: float) -> float:
    rules = {
        "gdp_growth":            lambda v: max(-1, min(1, v / 4)),
        "inflation":             lambda v: max(-1, min(1, (3 - v) / 3)),
        "unemployment":          lambda v: max(-1, min(1, (5 - v) / 3)),
        "fed_rate":              lambda v: max(-1, min(1, (4 - v) / 4)),
        "yield_curve":           lambda v: max(-1, min(1, v)),
        "consumer_sentiment":    lambda v: max(-1, min(1, (v - 70) / 30)),
        "industrial_production": lambda v: max(-1, min(1, v / 4)),
    }
    return rules.get(key, lambda v: 0.0)(value)


def compute_utility(state: dict, phase: str) -> dict[str, float]:
    """Berechnet Utility-Score für jedes Portfolio basierend auf Phase und State."""
    phase_w = PHASE_WEIGHTS.get(phase, PHASE_WEIGHTS["Abschwung"])
    scores: dict[str, float] = {}

    for portfolio, weights in phase_w.items():
        total = sum(
            weights.get(key, 0.0) * _normalize(key, value)
            for key, value in state.items()
        )
        scores[portfolio] = round(total, 4)

    return scores
