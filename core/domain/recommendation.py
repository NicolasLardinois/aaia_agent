from typing import Optional

from core.domain.models import (
    AnomalyReport, CockpitResult,
    InvestmentRecommendation, Recommendation, ShortType, Signal,
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

    score += _SEVERITY_DEDUCTION.get(td_anomaly.severity, 0.0)
    score += _SEVERITY_DEDUCTION.get(bu_anomaly.severity, 0.0)

    if regime_confidence < 0.4:
        score -= 0.10

    return round(max(0.10, min(1.0, score)), 2)


def derive_recommendation(
    alignment: str,
    signal: Signal,
    asset_class: str,
    in_portfolio: bool,
    market: str,
    cockpit: Optional[CockpitResult],
    top_down_available: bool,
    confidence: float,
    days_to_cover: Optional[float] = None,
    short_float_pct: Optional[float] = None,
) -> InvestmentRecommendation:

    market = market.upper().strip()

    if confidence < 0.35:
        return InvestmentRecommendation(
            action=Recommendation.HOLD,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning=(
                "Stark widersprüchliche oder anomale Signale — Cash bevorzugen, "
                "kein neues Kapital einsetzen."
            ),
        )
    if confidence < 0.50:
        return InvestmentRecommendation(
            action=Recommendation.HOLD,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning="Signallage zu widersprüchlich — Abwarten empfohlen.",
        )

    full_analysis = top_down_available and market in FULL_ANALYSIS_MARKETS
    bearish = signal == Signal.BEARISH or alignment == "aligned_bearish"
    bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

    if bearish and not in_portfolio and full_analysis:
        short_t = _short_type(asset_class)
        reasoning = "Bearish Signal ohne bestehende Portfolio-Position — Short möglich."
        if days_to_cover is not None and days_to_cover >= _DTC_SQUEEZE_THRESHOLD:
            reasoning += (
                f" ⚠️ Squeeze-/Borrow-Risiko: Days-to-Cover={days_to_cover:.1f}"
                + (f", Short-Float={short_float_pct:.0f}%" if short_float_pct is not None else "")
                + " — erhöhte Eindeckungskosten/Squeeze-Gefahr."
            )
        return InvestmentRecommendation(
            action=Recommendation.SHORT,
            short_type=short_t,
            short_warning=SHORT_WARNINGS[short_t],
            confidence=confidence,
            reasoning=reasoning,
        )

    if bearish and in_portfolio:
        return InvestmentRecommendation(
            action=Recommendation.SELL,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning="Bearish Signal bei bestehender Portfolio-Position — Verkauf empfohlen.",
        )

    if bullish and not in_portfolio:
        size = _position_size_pct(confidence)
        return InvestmentRecommendation(
            action=Recommendation.BUY,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning=(
                "Bullish Signal ohne bestehende Portfolio-Position — Kauf empfohlen. "
                f"Empfohlene Positionsgröße: {size:.1f}% des Risikobudgets "
                f"(konfidenz-skaliert)."
            ),
        )

    return InvestmentRecommendation(
        action=Recommendation.HOLD,
        short_type=None,
        short_warning=None,
        confidence=confidence,
        reasoning="Kein klares Kauf- oder Verkaufssignal — Position halten.",
    )
