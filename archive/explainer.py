"""
explainer.py — Erweiterung 10: Erklärbarkeit (XAI)
====================================================
Berechnet den Beitrag jedes Indikators zur finalen Entscheidung
und erzeugt eine menschenlesbare Zusammenfassung.
"""

from weights import PHASE_WEIGHTS, _normalize


class Explainer:
    def explain(
        self,
        state: dict,
        phase: str,
        decision: str,
        agent_votes: dict[str, dict],
    ) -> dict:
        """
        Erklärt, warum ein bestimmtes Portfolio ausgewählt wurde.

        Returns:
            explanation — Dict mit top_factors, agent_votes, summary
        """
        phase_w = PHASE_WEIGHTS.get(phase, {})
        portfolio_w = phase_w.get(decision, {})

        contributions = {}
        for indicator, weight in portfolio_w.items():
            value = state.get(indicator, 0.0)
            norm  = _normalize(indicator, value)
            contribution = weight * norm
            contributions[indicator] = {
                "value":        round(value, 3),
                "normalized":   round(norm, 3),
                "weight":       round(weight, 3),
                "contribution": round(contribution, 4),
            }

        sorted_factors = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]["contribution"]),
            reverse=True,
        )
        top_factors = dict(sorted_factors[:3])

        # Agenten-Konsens prüfen
        agent_agreement = sum(
            1 for votes in agent_votes.values()
            if max(votes, key=votes.get) == decision
        )
        total_agents = len(agent_votes)

        # Klartext-Zusammenfassung
        top_indicator = sorted_factors[0][0] if sorted_factors else "unbekannt"
        top_value     = sorted_factors[0][1]["value"] if sorted_factors else 0

        summary = (
            f"Empfehlung: {decision} (Phase: {phase}). "
            f"Stärkster Treiber: {top_indicator} = {top_value}. "
            f"Agenten-Konsens: {agent_agreement}/{total_agents}."
        )

        return {
            "decision":       decision,
            "phase":          phase,
            "top_factors":    top_factors,
            "all_contributions": contributions,
            "agent_votes":    agent_votes,
            "agent_agreement": f"{agent_agreement}/{total_agents}",
            "summary":        summary,
        }
