"""
portfolio.py — Erweiterung 1: Softmax-Portfolioallokation
==========================================================
Wandelt Utility-Scores in prozentuale Portfoliogewichte um (Softmax).
Bei zu niedriger Konfidenz wird Cash übergewichtet.
"""

import math

MIN_ALLOCATION = 0.05   # Mindestallokation pro Portfolio (5%)
CASH_FALLBACK  = 0.50   # Cash-Anteil bei niedriger Konfidenz


def _softmax(scores: dict[str, float], temperature: float = 1.0) -> dict[str, float]:
    """Softmax-Transformation über alle Portfolio-Scores."""
    exp_vals = {k: math.exp(v / temperature) for k, v in scores.items()}
    total    = sum(exp_vals.values())
    return {k: v / total for k, v in exp_vals.items()}


class PortfolioAllocator:
    def allocate(
        self,
        scores: dict[str, float],
        confidence: float,
        is_sufficient: bool,
    ) -> dict[str, float]:
        """
        Berechnet die Portfolioallokation.

        Args:
            scores        — Utility-Score pro Portfolio
            confidence    — Gesamtkonfidenz [0, 1]
            is_sufficient — ob die Konfidenz ausreicht

        Returns:
            allocation — Prozentualer Anteil pro Portfolio (summiert auf 1.0)
        """
        if not is_sufficient:
            return self._shift_to_cash(scores)

        raw = _softmax(scores, temperature=0.5)

        # Mindestallokation sicherstellen
        adjusted = {k: max(v, MIN_ALLOCATION) for k, v in raw.items()}
        total    = sum(adjusted.values())
        normalized = {k: round(v / total, 4) for k, v in adjusted.items()}

        return normalized

    def _shift_to_cash(self, scores: dict[str, float]) -> dict[str, float]:
        """Verschiebt bei niedriger Konfidenz CASH_FALLBACK zu Cash."""
        raw   = _softmax(scores, temperature=1.0)
        other = {k: v * (1 - CASH_FALLBACK) for k, v in raw.items() if k != "Cash"}
        total = sum(other.values())
        other = {k: round(v / total * (1 - CASH_FALLBACK), 4) for k, v in other.items()}
        other["Cash"] = round(CASH_FALLBACK, 4)
        return other

    def best_portfolio(self, allocation: dict[str, float]) -> str:
        return max(allocation, key=allocation.get)
