"""
anomaly.py — Erweiterung 9: Anomalie-Erkennung
================================================
Erkennt statistische Ausreisser in den aktuellen Wirtschaftsdaten
mittels Z-Score über historische Werte (aus dem Gedächtnis oder raw-Daten).
"""

import math

Z_THRESHOLD = 2.5


class AnomalyDetector:
    def check(
        self,
        current_state: dict[str, float],
        history: list[dict],
    ) -> tuple[bool, list[dict]]:
        """
        Vergleicht jeden Indikator mit seiner historischen Verteilung.

        Args:
            current_state — aktueller Wirtschafts-State
            history       — Liste vergangener States (aus AgentMemory)

        Returns:
            is_anomaly — True wenn mindestens eine Anomalie gefunden
            anomalies  — Liste mit Details zu jeder Anomalie
        """
        if len(history) < 5:
            return False, []

        anomalies = []

        for key, current_val in current_state.items():
            past_vals = [
                e.get("state", {}).get(key)
                for e in history
                if e.get("state", {}).get(key) is not None
            ]
            if len(past_vals) < 3:
                continue

            mean = sum(past_vals) / len(past_vals)
            variance = sum((v - mean) ** 2 for v in past_vals) / len(past_vals)
            std = math.sqrt(variance) if variance > 0 else 0.0

            if std == 0:
                continue

            z_score = (current_val - mean) / std

            if abs(z_score) > Z_THRESHOLD:
                direction = "hoch" if z_score > 0 else "niedrig"
                anomalies.append({
                    "indicator": key,
                    "current":   round(current_val, 3),
                    "mean":      round(mean, 3),
                    "std":       round(std, 3),
                    "z_score":   round(z_score, 3),
                    "direction": direction,
                })

        return len(anomalies) > 0, anomalies
