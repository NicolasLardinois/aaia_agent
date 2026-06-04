from core.domain.models import MarketRegime


def _score_indicator(key: str, value: float) -> float:
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


_PHASE_THRESHOLDS = [
    (MarketRegime.BOOM,      0.60),
    (MarketRegime.EXPANSION, 0.20),
    (MarketRegime.RECOVERY, -0.10),
    (MarketRegime.SLOWDOWN, -0.40),
    (MarketRegime.RECESSION, -1.00),
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


class RegimeDetector:
    def detect(self, state: dict) -> tuple[MarketRegime, float, dict]:
        """
        Returns: (regime, confidence, evidence_per_indicator)
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

        regime = MarketRegime.SLOWDOWN
        for r, threshold in _PHASE_THRESHOLDS:
            if composite >= threshold:
                regime = r
                break

        confidence = round(min(1.0, abs(composite) * 1.5 + 0.3), 3)
        return regime, confidence, evidence
