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

# Länderspezifische Buffett-Fallback-Korridore (bullish_unter, bearish_über) in %
_BUFFETT_CORRIDORS: dict[str, tuple[float, float]] = {
    "USA": (75.0, 135.0),
    "CHE": (150.0, 260.0),    # CH strukturell hoch (SMI-Schwergewichte)
    "DEU": (40.0, 70.0),      # DE strukturell niedrig
    "FRA": (60.0, 110.0),
    "ITA": (20.0, 50.0),
}
_BUFFETT_DEFAULT_CORRIDOR = (75.0, 135.0)


def _buffett_fallback_note(code: str, ratio: float) -> list[str]:
    """Länderspezifischer Fallback-Korridor statt globaler 75/135%-Schwelle."""
    low, high = _BUFFETT_CORRIDORS.get(code, _BUFFETT_DEFAULT_CORRIDOR)
    label = f"Buffett-Indikator {code}"
    if ratio > high:
        return [f"{label} {ratio:.0f}% — Markt teuer (>{high:.0f}% für {code})"]
    if ratio < low:
        return [f"{label} {ratio:.0f}% — Markt günstig (<{low:.0f}% für {code})"]
    return []


# Asset-Klassen für die der Buffett-Indikator relevant ist (Marktkapitalisierung / BIP)
_BUFFETT_RELEVANT_ASSETS = {"equity", "etf", "index"}


def _buffett_notes(countries: dict, market: str, asset_class: str) -> list[str]:
    """
    Buffett-Kontexthinweis für das analysierte Land.
    Nur relevant für Aktien, ETFs und Indizes — nicht für Anleihen, Rohstoffe, Edelmetalle.
    Verwendet Z-Score gegen die eigene 10J-Geschichte (falls vorhanden),
    sonst länderspezifischer Fallback-Korridor (kein globaler 75/135%-Fix).
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
    # Fallback auf länderspezifischen Korridor (kein globaler 75/135%-Fix)
    return _buffett_fallback_note(code, r)


_EUROZONE_ISO2 = {
    "AT", "BE", "CY", "EE", "ES", "FI", "FR",
    "GR", "HR", "IE", "IT", "LT", "LU", "LV", "MT",
    "NL", "PT", "SI", "SK",
}


def _sovereign_spread_note(market: str, sovereign_spreads) -> list[str]:
    """Länderspezifischer Spread vs Bund — nur für Eurozone-Aktien (nicht DE)."""
    m = market.upper()
    if m not in _EUROZONE_ISO2:
        return []
    spreads = getattr(sovereign_spreads, "spreads_by_country", {})
    spread = spreads.get(f"{m}_10y")
    if not isinstance(spread, (int, float)):
        return []
    if spread > 300:
        return [f"Sovereign Spread {m}-Bund {spread:.0f}bp — Krisenniveau (>300bp)"]
    if spread > 150:
        return [f"Sovereign Spread {m}-Bund {spread:.0f}bp — erhöht (>150bp)"]
    return []


def _yield_region(market: str) -> str:
    m = market.upper()
    if m == "USA":
        return "usa"
    if m in ("CH", "CHE"):
        return "switzerland"
    return "eurozone"


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

    yield_pt = getattr(cockpit.yield_curve.yield_spreads, _yield_region(market))
    if yield_pt.inverted:
        spread_str = f"{yield_pt.spread_10y2y:+.2f}" if yield_pt.spread_10y2y is not None else "n/a"
        notes.append(f"Zinskurve invertiert ({spread_str}) — Rezessionsrisiko erhöht")

    vix_value = cockpit.sentiment.vix.vix
    if vix_value is not None and vix_value > 30:
        notes.append(f"VIX {vix_value:.1f} signalisiert erhöhte Unsicherheit")

    leading = cockpit.sectors.performance.leading_usa
    if leading and leading != sector:
        notes.append(f"Führender Sektor derzeit: {leading}")

    buffett_countries = getattr(cockpit.macro.buffett_indicator, "countries", {})
    notes.extend(_buffett_notes(buffett_countries, market, asset_class))

    notes.extend(_sovereign_spread_note(market, cockpit.yield_curve.sovereign_spreads))

    suffix = ". ".join(notes)
    result = f"[{regime.value}] {context}"
    if suffix:
        result += f". {suffix}"
    return result
