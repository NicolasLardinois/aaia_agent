from typing import Optional

from core.domain.models import (
    AnomalyReport, CockpitResult,
    InvestmentRecommendation, PositionState, Recommendation, ShortAction, ShortType, Signal,
)

# Alle Märkte mit vollständigem Top-Down-Kontext (Makrodaten vorhanden):
# USA → FRED, CH → SNB, Eurozone-Länder → EZB
_EUROZONE_MARKETS = {
    "DE", "FR", "IT", "ES", "NL", "AT", "BE", "PT",
    "FI", "IE", "GR", "SK", "SI", "EE", "LV", "LT",
    "LU", "MT", "CY",
}
FULL_ANALYSIS_MARKETS = {"USA", "CH"} | _EUROZONE_MARKETS

SHORT_WARNINGS = {
    ShortType.DEFENSIVE: (
        "⚠️ SHORTPOSITION — DEFENSIV\n"
        "Hierbei handelt es sich um eine Short-Position zur Absicherung "
        "des Portfolios gegen fallende Kurse von ETFs oder Indizes."
    ),
    ShortType.AGGRESSIVE: (
        "⚠️ SHORTPOSITION — AGGRESSIV\n"
        "Hierbei handelt es sich um eine spekulative Short-Position mit der "
        "Absicht, von fallenden Kursen eines Einzelwerts zu profitieren "
        "(Einzelaktien, Edelmetalle, Rohstoffe, Anleihen)."
    ),
}

ETF_ASSET_CLASSES       = {"etf", "index"}
AGGRESSIVE_ASSET_CLASSES = {"equity", "precious_metal", "commodity", "bond"}

_SEVERITY_DEDUCTION = {"none": 0.0, "low": -0.05, "medium": -0.15, "high": -0.25}
_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
_CALIB_MIN_N = 10
_DTC_SQUEEZE_THRESHOLD = 5.0   # Days-to-Cover ab dem ein Squeeze-Risiko vermerkt wird


def _short_type(asset_class: str) -> ShortType:
    if asset_class.lower() in ETF_ASSET_CLASSES:
        return ShortType.DEFENSIVE
    return ShortType.AGGRESSIVE


def _combined_severity(a: str, b: str) -> str:
    rank = max(_SEVERITY_ORDER.get(a, 0), _SEVERITY_ORDER.get(b, 0))
    for name, r in _SEVERITY_ORDER.items():
        if r == rank:
            return name
    return "none"


def _position_size_pct(confidence: float) -> float:
    """Fractional-Sizing: lineares Mapping Konfidenz→Positionsgröße, gedeckelt 2–10 %."""
    raw = (confidence - 0.50) / 0.50 * 10.0   # 0.50→0 %, 1.00→10 %
    return round(max(2.0, min(10.0, raw)), 1)


def _anomaly_deduction(alignment: str, report: AnomalyReport) -> float:
    """Bestätigt die Anomalie-Richtung die These (bearish↔aligned_bearish, bullish↔aligned_bullish)?
    Dann kein Abzug. Sonst (widersprechend/neutral/nicht-aligned) Severity-Abzug wie bisher."""
    confirms = (
        (alignment == "aligned_bearish" and report.direction == "bearish") or
        (alignment == "aligned_bullish" and report.direction == "bullish")
    )
    if confirms:
        return 0.0
    return _SEVERITY_DEDUCTION.get(report.severity, 0.0)


def compute_confidence(
    alignment: str,
    regime_confidence: float,
    td_anomaly: AnomalyReport,
    bu_anomaly: AnomalyReport,
    calibration: Optional[dict] = None,
) -> float:
    # Basis: historisch kalibrierte bedingte Trefferrate je (alignment, severity)-Bucket.
    # Keys sind Strings im Format "alignment:severity" (JSON-serialisierbar, Tuple-Keys
    # würden nach JSON-Roundtrip durch Memory-Persistenz verloren gehen).
    # TODO: Bucket-Befüllung ist eine dokumentierte Folge-Aufgabe — sie erfordert, dass
    # alignment und severity je Trade in der History persistiert werden (kein Producer
    # existiert noch; derzeit daher stets Fallback 0.70).
    sev = _combined_severity(td_anomaly.severity, bu_anomaly.severity)
    base = 0.70
    if calibration:
        key = f"{alignment}:{sev}"
        bucket = calibration.get(key)
        if bucket and bucket.get("n", 0) >= _CALIB_MIN_N and bucket.get("hit_rate") is not None:
            base = float(bucket["hit_rate"])

    score = base

    if alignment in ("aligned_bullish", "aligned_bearish"):
        score += 0.10
    elif alignment == "contradicting":
        score -= 0.15
    elif alignment == "mixed":
        score -= 0.05

    score += _anomaly_deduction(alignment, td_anomaly)
    score += _anomaly_deduction(alignment, bu_anomaly)

    if regime_confidence < 0.4:
        score -= 0.10

    return round(max(0.10, min(1.0, score)), 2)


def derive_recommendation(
    alignment: str,
    signal: Signal,
    asset_class: str,
    current_position: PositionState,
    market: str,
    cockpit: Optional[CockpitResult],
    top_down_available: bool,
    confidence: float,
) -> InvestmentRecommendation:
    # Titel als Short gehalten → Long-Linse deferiert (kein "BUY, obwohl short").
    if current_position == PositionState.SHORT:
        return InvestmentRecommendation(
            action=Recommendation.NONE, short_type=None, short_warning=None,
            confidence=confidence,
            reasoning="Titel als Short gehalten — Long-Seite deferiert (Short-Linse/PM zuständig).",
        )

    is_long = current_position == PositionState.LONG
    bearish = signal == Signal.BEARISH or alignment == "aligned_bearish"
    bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

    # Uneindeutig/anomal → keine Aktion (positionsabhängig)
    if confidence < 0.50:
        action = Recommendation.HOLD if is_long else Recommendation.NONE
        reasoning = ("Stark widersprüchliche/anomale Signale — Cash bevorzugen, kein neues Kapital."
                     if confidence < 0.35 else
                     "Signallage zu widersprüchlich — Abwarten empfohlen.")
        return InvestmentRecommendation(action, None, None, confidence, reasoning)

    if is_long:
        if bearish:
            action = Recommendation.SELL
            reasoning = "Bearish bei bestehender Long-Position — Verkauf empfohlen."
        elif bullish:
            size = _position_size_pct(confidence)
            action = Recommendation.BUY_PLUS
            reasoning = (f"Bullish bei bestehender Long-Position — Aufstocken. "
                         f"Zusätzliche Tranche ~{size:.1f}% des Risikobudgets (konfidenz-skaliert).")
        else:
            action = Recommendation.HOLD
            reasoning = "Kein klares Signal — Position halten."
    else:  # PositionState.NONE
        if bullish:
            size = _position_size_pct(confidence)
            action = Recommendation.BUY
            reasoning = (f"Bullish ohne bestehende Position — Kauf empfohlen. "
                         f"Empfohlene Positionsgröße: {size:.1f}% des Risikobudgets (konfidenz-skaliert).")
        else:
            action = Recommendation.NONE
            reasoning = "Kein Long-Setup (kein bullisches Signal)."

    return InvestmentRecommendation(action, None, None, confidence, reasoning)


def derive_short_action_placeholder(current_position: PositionState) -> ShortAction:
    """Platzhalter bis zur Short-Thesis-Engine (Block 1).
    short gehalten → HOLD; sonst → NONE (bei LONG deferiert die Short-Linse —
    man shortet nicht, was man besitzt). Block 1 muss Defer-on-LONG beibehalten."""
    return ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE


def detect_conflict(current_position, alignment, dominant_signal, short_assessment, long_confidence):
    """Bidirektional: gehaltene Position vs. gegenläufiges Linsen-Signal."""
    if current_position == PositionState.LONG:
        if short_assessment.confidence >= 0.50 and short_assessment.archetypes:
            return True, (f"Long gehalten, screent aber als Short "
                          f"(Konfidenz {short_assessment.confidence:.0%}; "
                          f"{', '.join(short_assessment.archetypes)}) — Long-These prüfen (evtl. SELL).")
    if current_position == PositionState.SHORT:
        bullish = alignment == "aligned_bullish" or dominant_signal == Signal.BULLISH
        if bullish and long_confidence >= 0.50:
            return True, (f"Short gehalten, screent aber bullish "
                          f"(Long-Konfidenz {long_confidence:.0%}) — Short-These prüfen (evtl. COVER).")
    return False, ""
