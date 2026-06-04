from core.domain.events import TopDownContextReady
from core.domain.models import CockpitResult, MarketRegime
from core.ports.event_bus import EventBus

REGIME_SECTOR_CONTEXT: dict[MarketRegime, dict[str, str]] = {
    MarketRegime.BOOM: {
        "Technology":   "Outperformt historisch in Boom-Phasen",
        "Energy":       "Profitiert von hoher Nachfrage",
        "Financials":   "Günstig bei steigenden Zinsen",
        "default":      "Aktien generell stark in Boom-Phasen",
    },
    MarketRegime.RECESSION: {
        "Healthcare":   "Defensiver Sektor, krisenresistent",
        "ConsumerStap": "Basiskonsum bleibt stabil",
        "Utilities":    "Sicher, aber limitiertes Upside",
        "default":      "Historisch schwieriges Umfeld für Aktien",
    },
    MarketRegime.SLOWDOWN: {
        "default": "Late-Cycle: Selektivität wichtig, Qualität bevorzugen",
    },
    MarketRegime.EXPANSION: {
        "default": "Breite Marktpartizipation möglich",
    },
    MarketRegime.RECOVERY: {
        "default": "Früh-Zykliker profitieren überproportional",
    },
}


class TopDownContextAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    def run(self, cockpit: CockpitResult, ticker_sector: str = "default") -> str:
        regime = cockpit.macro.regime
        context_map = REGIME_SECTOR_CONTEXT.get(regime, {})
        context = context_map.get(ticker_sector) or context_map.get("default", "")

        yield_note = ""
        if cockpit.yield_curve.inverted:
            yield_note = " Zinskurve invertiert — Rezessionsrisiko erhöht."

        vix_note = ""
        if cockpit.sentiment.vix > 30:
            vix_note = f" VIX={cockpit.sentiment.vix:.1f} signalisiert hohe Unsicherheit."

        full_context = f"[{regime.value}] {context}{yield_note}{vix_note}"
        self.bus.publish(TopDownContextReady(source="top_down_context_agent", payload={"context": full_context}))
        return full_context
