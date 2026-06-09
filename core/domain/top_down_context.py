from core.domain.models import CockpitResult, MarketRegime, Signal

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
    MarketRegime.DEPRESSION: {
        "Healthcare":   "Nachfrage strukturell stabil — defensiv in extremer Abschwächung",
        "ConsumerStap": "Basiskonsum hält auch unter extremem Druck",
        "Gold":         "Klassischer sicherer Hafen in tiefen Krisen — Kapitalerhalt",
        "Technology":   "Extremes Bewertungsrisiko, lange Erholungszeiten möglich",
        "Financials":   "Kreditausfälle, Systemrisiken — erhöhtes Verlustpotenzial",
        "default":      "Tiefstes Krisentief: Kapitalerhalt absoluter Fokus, keine Wachstumswetten",
    },
}


# Mapping von market-Parameter (ISO-2 oder System-Kürzel) auf ISO-3 für Weltbank/FRED.
# Es gibt keine "EU"-Aktie — immer das spezifische Land angeben (DE, FR, IT, ...).
_MARKET_COUNTRY: dict[str, str] = {
    # System-Kürzel
    "USA": "USA",
    "CH":  "CHE",
    # ISO-2 → ISO-3 (häufige Märkte)
    "DE":  "DEU",
    "FR":  "FRA",
    "IT":  "ITA",
    "ES":  "ESP",
    "NL":  "NLD",
    "AT":  "AUT",
    "BE":  "BEL",
    "PT":  "PRT",
    "FI":  "FIN",
    "IE":  "IRL",
    "GR":  "GRC",
    "SE":  "SWE",
    "DK":  "DNK",
    "NO":  "NOR",
    "UK":  "GBR",
    "JP":  "JPN",
    "CN":  "CHN",
    "AU":  "AUS",
    "CA":  "CAN",
    "KR":  "KOR",
    "IN":  "IND",
    "BR":  "BRA",
    # ISO-3 direkt (falls jemand bereits ISO-3 übergibt)
    "CHE": "CHE",
    "DEU": "DEU",
    "FRA": "FRA",
    "ITA": "ITA",
    "ESP": "ESP",
    "GBR": "GBR",
    "JPN": "JPN",
    "CHN": "CHN",
    "AUS": "AUS",
    "CAN": "CAN",
}

_BUFFETT_BEARISH = 135.0
_BUFFETT_BULLISH = 75.0


# Asset-Klassen für die der Buffett-Indikator relevant ist (Marktkapitalisierung / BIP)
_BUFFETT_RELEVANT_ASSETS = {"equity", "etf", "index"}


def _buffett_notes(countries: dict, market: str, asset_class: str) -> list[str]:
    """
    Buffett-Kontexthinweis für das analysierte Land.
    Nur relevant für Aktien, ETFs und Indizes — nicht für Anleihen, Rohstoffe, Edelmetalle.
    Verwendet Z-Score gegen die eigene 10J-Geschichte (falls vorhanden),
    sonst Fallback auf absolute Schwellenwerte.
    """
    if asset_class.lower() not in _BUFFETT_RELEVANT_ASSETS:
        return []
    if not countries:
        return []

    code  = _MARKET_COUNTRY.get(market.upper(), "USA")
    point = countries.get(code)
    if point is None or point.ratio_pct is None:
        return []

    r     = point.ratio_pct
    z     = point.z_score
    label = f"Buffett-Indikator {code}"

    if z is not None:
        if z >= 1.5:
            return [f"{label} {r:.0f}% — historisch erhöht (Z=+{z:.1f})"]
        if z <= -1.5:
            return [f"{label} {r:.0f}% — historisch niedrig (Z={z:.1f})"]
        return []
    # Fallback auf absolute Schwellen wenn keine Länder-Historie verfügbar
    if r > _BUFFETT_BEARISH:
        return [f"{label} {r:.0f}% — Markt teuer (>135%)"]
    if r < _BUFFETT_BULLISH:
        return [f"{label} {r:.0f}% — Markt günstig (<75%)"]
    return []


def derive_top_down_context(
    cockpit: CockpitResult,
    sector: str = "default",
    market: str = "USA",
    asset_class: str = "equity",
) -> str:
    regime      = cockpit.macro.regime
    context_map = _REGIME_CONTEXT.get(regime, {})
    context     = context_map.get(sector) or context_map.get("default", "")

    notes: list[str] = []

    usa_yield = cockpit.yield_curve.yield_spreads.usa
    if usa_yield.inverted:
        spread_str = f"{usa_yield.spread_10y2y:+.2f}" if usa_yield.spread_10y2y is not None else "n/a"
        notes.append(f"Zinskurve invertiert ({spread_str}) — Rezessionsrisiko erhöht")

    vix_value = cockpit.sentiment.vix.vix
    if vix_value is not None and vix_value > 30:
        notes.append(f"VIX {vix_value:.1f} signalisiert erhöhte Unsicherheit")

    leading = cockpit.sectors.performance.leading_usa
    if leading and leading != sector:
        notes.append(f"Führender Sektor derzeit: {leading}")

    buffett_countries = getattr(cockpit.macro.buffett_indicator, "countries", {})
    notes.extend(_buffett_notes(buffett_countries, market, asset_class))

    suffix = ". ".join(notes)
    result = f"[{regime.value}] {context}"
    if suffix:
        result += f". {suffix}"
    return result
