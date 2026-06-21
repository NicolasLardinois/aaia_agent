from core.domain.models import Signal, RiskAffinity, CreditBand

_SICHER  = {"AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"}
_MITTEL  = {"BB+", "BB", "BB-", "B+", "B", "B-"}
_RISKANT = {"CCC+", "CCC", "CCC-", "CC", "C", "D"}


def rating_to_band(rating: str | None) -> CreditBand | None:
    """S&P-Langfristrating → Credit-Band. Unbekannt/fehlend → None (Credit unverfügbar)."""
    if rating is None:
        return None
    r = rating.strip().upper()
    if r in _SICHER:
        return CreditBand.SICHER
    if r in _MITTEL:
        return CreditBand.MITTEL
    if r in _RISKANT:
        return CreditBand.RISKANT
    return None


_CONTRIB: dict[CreditBand, dict[RiskAffinity, float]] = {
    CreditBand.SICHER:  {RiskAffinity.KONSERVATIV: 0.0, RiskAffinity.NEUTRAL: 0.0,  RiskAffinity.RISIKOFREUDIG: 0.0},
    CreditBand.MITTEL:  {RiskAffinity.KONSERVATIV: -1.0, RiskAffinity.NEUTRAL: -0.5, RiskAffinity.RISIKOFREUDIG: 0.0},
    CreditBand.RISKANT: {RiskAffinity.KONSERVATIV: -1.5, RiskAffinity.NEUTRAL: -1.0, RiskAffinity.RISIKOFREUDIG: -0.5},
}


def credit_contribution(band: CreditBand, affinity: RiskAffinity) -> float:
    """Numerischer Credit-Beitrag = f(Band, Risikoaffinität). Nie positiv: Ausfallrisiko
    ist kein Pluspunkt — die Rendite belohnt separat über das metrics-Signal."""
    return _CONTRIB[band][affinity]


_SCORE = {Signal.BULLISH: 1.0, Signal.NEUTRAL: 0.0, Signal.BEARISH: -1.0}
_THRESHOLD = 0.15


def aggregate_bond_signal(
    metrics: Signal | None,
    duration: Signal | None,
    spread: Signal | None,
    credit_band: CreditBand | None,
    affinity: RiskAffinity,
) -> tuple[Signal, float]:
    """Gleich gewichteter Mittelwert der verfügbaren Komponenten (kein Veto).
    metrics/duration/spread → ±1/0; credit → Beitrag (Band × Affinität, bis -1.5).
    Unverfügbare Komponente (None) wird weggelassen → restliche re-normalisiert."""
    parts: list[float] = []
    for sig in (metrics, duration, spread):
        if sig is not None:
            parts.append(_SCORE[sig])
    if credit_band is not None:
        parts.append(credit_contribution(credit_band, affinity))
    if not parts:
        return Signal.NEUTRAL, 0.0
    net = sum(parts) / len(parts)
    confidence = min(1.0, abs(net))
    if net > _THRESHOLD:
        return Signal.BULLISH, confidence
    if net < -_THRESHOLD:
        return Signal.BEARISH, confidence
    return Signal.NEUTRAL, confidence
