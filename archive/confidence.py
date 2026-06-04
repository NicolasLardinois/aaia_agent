"""
confidence.py — Erweiterung 6: Konfidenz & Unsicherheitsquantifizierung
========================================================================
Berechnet eine Gesamtkonfidenz aus drei Komponenten:
  40% Score-Gap (Abstand zwischen bestem und zweitbestem Portfolio)
  30% Volatilität (niedrige Volatilität = höhere Konfidenz)
  30% Phasen-Konfidenz (vom PhaseDetector geliefert)
"""

MIN_CONFIDENCE = 0.4
MIN_SCORE_GAP  = 0.5


class ConfidenceCalculator:
    def compute(
        self,
        scores: dict[str, float],
        volatility: dict[str, float],
        phase_confidence: float,
    ) -> tuple[float, dict]:
        """
        Returns:
            confidence  — Gesamtkonfidenz [0, 1]
            breakdown   — Erklärung der Teilkomponenten
        """
        sorted_scores = sorted(scores.values(), reverse=True)
        best   = sorted_scores[0] if len(sorted_scores) > 0 else 0.0
        second = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

        raw_gap  = best - second
        gap_conf = min(1.0, raw_gap / 2.0)   # normiert auf [0,1]

        # Durchschnittliche Volatilität → niedrig = gut
        avg_vol = sum(volatility.values()) / len(volatility) if volatility else 1.0
        vol_conf = max(0.0, 1.0 - min(1.0, avg_vol / 3.0))

        total_conf = round(
            0.40 * gap_conf +
            0.30 * vol_conf +
            0.30 * phase_confidence,
            3,
        )

        breakdown = {
            "score_gap":        round(raw_gap, 4),
            "gap_confidence":   round(gap_conf, 3),
            "vol_confidence":   round(vol_conf, 3),
            "phase_confidence": round(phase_confidence, 3),
            "total":            total_conf,
        }
        return total_conf, breakdown

    def is_sufficient(self, confidence: float, scores: dict[str, float]) -> bool:
        """True wenn Konfidenz und Score-Gap über den Mindest-Schwellenwerten liegen."""
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        return confidence >= MIN_CONFIDENCE and gap >= MIN_SCORE_GAP
