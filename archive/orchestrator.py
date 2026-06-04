"""
orchestrator.py — Erweiterung 8: Orchestrator für Multi-Agenten-System
=======================================================================
Konsolidiert die Stimmen aller Spezialagenten zu einem gemeinsamen Score.
Gewichte: Makroökonom 35%, Arbeitsmarkt 20%, Marktsentiment 25%, Risiko 20%
"""

from specialist_agents import MacroAgent, LaborAgent, SentimentAgent, RiskAgent

AGENT_WEIGHTS: dict[str, float] = {
    "Makroökonom":    0.35,
    "Arbeitsmarkt":   0.20,
    "Marktsentiment": 0.25,
    "Risiko":         0.20,
}

PORTFOLIOS = ["Aktien", "Anleihen", "Cash", "Gold"]


class Orchestrator:
    def __init__(self):
        self.agents = [MacroAgent(), LaborAgent(), SentimentAgent(), RiskAgent()]

    def consolidate(
        self, state: dict, phase: str
    ) -> tuple[dict[str, float], dict[str, dict]]:
        """
        Aggregiert alle Agenten-Stimmen gewichtet.

        Returns:
            final_scores  — gewichteter Portfolio-Score
            agent_votes   — Einzelstimmen aller Agenten
        """
        agent_votes: dict[str, dict] = {}

        for agent in self.agents:
            agent_votes[agent.name] = agent.vote(state, phase)

        final_scores: dict[str, float] = {p: 0.0 for p in PORTFOLIOS}

        for agent_name, vote in agent_votes.items():
            w = AGENT_WEIGHTS.get(agent_name, 0.0)
            for portfolio in PORTFOLIOS:
                final_scores[portfolio] += w * vote.get(portfolio, 0.0)

        final_scores = {p: round(v, 4) for p, v in final_scores.items()}
        return final_scores, agent_votes

    def best_portfolio(self, scores: dict[str, float]) -> str:
        return max(scores, key=scores.get)
