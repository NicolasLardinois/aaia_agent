from core.domain.models import CockpitResult, MarketRegime

_REGIME_CONTEXT: dict[MarketRegime, dict[str, str]] = {
    MarketRegime.BOOM: {
        "Technology":  "Outperformt historisch in Boom-Phasen bei hohem Wachstum",
        "Energy":      "Profitiert von starker Nachfrage und hohen Rohstoffpreisen",
        "Financials":  "Günstig bei steigenden Zinsen und hoher Kreditnachfrage",
        "default":     "Breites Marktumfeld positiv — zyklische Werte bevorzugt",
    },
    MarketRegime.EXPANSION: {
        "Technology":  "Wachstumswerte profitieren von positiven Kredit- und Investitionsbedingungen",
        "default":     "Breite Marktpartizipation möglich — risikobehaftete Assets begünstigt",
    },
    MarketRegime.SLOWDOWN: {
        "Technology":  "Late-Cycle: Bewertungsrisiko erhöht, Qualität und Cashflow zählen mehr",
        "Healthcare":  "Defensiver Charakter schützt in Verlangsamungsphasen",
        "default":     "Late-Cycle: Selektivität wichtig — Qualitätswerte gegenüber Spekulation bevorzugen",
    },
    MarketRegime.RECESSION: {
        "Healthcare":   "Krisenresistent — Nachfrage unabhängig vom Konjunkturzyklus",
        "ConsumerStap": "Basiskonsum bleibt stabil, auch in Abschwüngen",
        "Utilities":    "Defensiv und dividendenstark, aber begrenztes Upside",
        "Technology":   "Historisch schwieriges Umfeld — Bewertungskompression möglich",
        "default":      "Rezessionsumfeld: defensiv positionieren, Kapitalerhalt priorisieren",
    },
    MarketRegime.RECOVERY: {
        "Technology":  "Früh-Zykliker profitieren überproportional bei Erholung",
        "Financials":  "Kreditvergabe steigt — Banken und Versicherungen erholen sich",
        "default":     "Erholung begünstigt zyklische Werte und kleine Unternehmen",
    },
}


def derive_top_down_context(cockpit: CockpitResult, sector: str = "default") -> str:
    regime      = cockpit.macro.regime
    context_map = _REGIME_CONTEXT.get(regime, {})
    context     = context_map.get(sector) or context_map.get("default", "")

    notes: list[str] = []

    usa_yield = cockpit.yield_curve.yield_spreads.usa
    if usa_yield.inverted:
        notes.append(f"Zinskurve invertiert ({usa_yield.spread_10y2y:+.2f}) — Rezessionsrisiko erhöht")

    vix_value = cockpit.sentiment.vix.vix
    if vix_value is not None and vix_value > 30:
        notes.append(f"VIX {vix_value:.1f} signalisiert erhöhte Unsicherheit")

    leading = cockpit.sectors.performance.leading_usa
    if leading and leading != sector:
        notes.append(f"Führender Sektor derzeit: {leading}")

    suffix = ". ".join(notes)
    result = f"[{regime.value}] {context}"
    if suffix:
        result += f". {suffix}"
    return result
