"""
backtester.py — Erweiterung 7: Selbst-Evaluation / Backtesting
===============================================================
Vergleicht vergangene Entscheidungen mit dem heutigen besten Score,
um zu beurteilen, ob frühere Entscheidungen rückblickend korrekt waren.
"""

LOOKBACK = 3   # Anzahl vergangener Entscheidungen, die geprüft werden


class Backtester:
    def evaluate(
        self,
        memory_entries: list[dict],
        current_best: str,
        current_scores: dict[str, float],
    ) -> dict:
        """
        Vergleicht die letzten LOOKBACK Entscheidungen mit dem aktuellen Optimum.

        Returns:
            verdict — Dict mit Accuracy, Abweichungen und Empfehlung
        """
        if not memory_entries:
            return {"status": "Kein Gedächtnis vorhanden", "accuracy": None}

        recent = memory_entries[-LOOKBACK:]
        correct = 0
        deviations = []

        for entry in recent:
            past_decision = entry.get("decision", "")
            past_scores   = entry.get("scores", {})
            past_best     = max(past_scores, key=past_scores.get) if past_scores else ""

            was_correct = past_best == current_best
            score_diff  = abs(
                current_scores.get(past_decision, 0) - current_scores.get(current_best, 0)
            )

            if was_correct:
                correct += 1

            deviations.append({
                "timestamp":    entry.get("timestamp", ""),
                "past_decision": past_decision,
                "current_best": current_best,
                "was_correct":  was_correct,
                "score_diff":   round(score_diff, 4),
            })

        accuracy = correct / len(recent) if recent else 0.0
        trend    = "stabil" if accuracy >= 0.67 else "inkonsistent"

        return {
            "status":     trend,
            "accuracy":   round(accuracy, 3),
            "lookback":   len(recent),
            "correct":    correct,
            "deviations": deviations,
            "recommendation": (
                "Entscheidungslogik solide — weiter verfolgen."
                if accuracy >= 0.67
                else "Entscheidungslogik überprüfen — hohe Abweichung von Vergangenheit."
            ),
        }
