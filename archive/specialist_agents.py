"""
specialist_agents.py — Erweiterung 8: Multi-Agenten-System
===========================================================
Vier spezialisierte Agenten analysieren jeweils ihren Fachbereich:
  - MacroAgent:      BIP, Inflation, Leitzins
  - LaborAgent:      Arbeitslosigkeit, Konsumentenstimmung
  - SentimentAgent:  Zinskurve, Industrieproduktion
  - RiskAgent:       Regelbasierte Risikobewertung
"""

from weights import compute_utility


class MacroAgent:
    """Makroökonom: fokussiert auf gesamtwirtschaftliche Lage."""
    name = "Makroökonom"
    keys = ["gdp_growth", "inflation", "fed_rate"]

    def vote(self, state: dict, phase: str) -> dict[str, float]:
        sub_state = {k: state[k] for k in self.keys if k in state}
        full_state = {k: state.get(k, 0.0) for k in state}
        # Berechne Utility nur mit eigenen Indikatoren (rest auf 0)
        zeroed = {k: (sub_state[k] if k in sub_state else 0.0) for k in state}
        return compute_utility(zeroed, phase)


class LaborAgent:
    """Arbeitsmarkt-Experte: fokussiert auf Beschäftigung und Konsumklima."""
    name = "Arbeitsmarkt"
    keys = ["unemployment", "consumer_sentiment"]

    def vote(self, state: dict, phase: str) -> dict[str, float]:
        zeroed = {k: (state[k] if k in self.keys else 0.0) for k in state}
        return compute_utility(zeroed, phase)


class SentimentAgent:
    """Marktsentiment-Analyst: fokussiert auf Zinskurve und Industrieproduktion."""
    name = "Marktsentiment"
    keys = ["yield_curve", "industrial_production"]

    def vote(self, state: dict, phase: str) -> dict[str, float]:
        zeroed = {k: (state[k] if k in self.keys else 0.0) for k in state}
        return compute_utility(zeroed, phase)


class RiskAgent:
    """Risiko-Manager: regelbasierte Risikobewertung ohne Utility-Funktion."""
    name = "Risiko"

    def vote(self, state: dict, phase: str) -> dict[str, float]:
        risk_score = 0.0

        if state.get("yield_curve", 0) < 0:
            risk_score -= 0.3
        if state.get("inflation", 0) > 5:
            risk_score -= 0.2
        if state.get("unemployment", 0) > 6:
            risk_score -= 0.2
        if state.get("gdp_growth", 0) < 0:
            risk_score -= 0.2
        if state.get("fed_rate", 0) > 5:
            risk_score -= 0.1

        # Positive Signale
        if state.get("consumer_sentiment", 0) > 85:
            risk_score += 0.2
        if state.get("industrial_production", 0) > 2:
            risk_score += 0.1

        risk_score = max(-1.0, min(1.0, risk_score))

        return {
            "Aktien":   round(risk_score, 3),
            "Anleihen": round(-risk_score * 0.5, 3),
            "Cash":     round(-risk_score * 0.3, 3),
            "Gold":     round(-risk_score * 0.2, 3),
        }
