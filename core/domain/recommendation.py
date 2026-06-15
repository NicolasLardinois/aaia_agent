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


def _short_type(asset_class: str) -> ShortType:
    if asset_class.lower() in ETF_ASSET_CLASSES:
        return ShortType.DEFENSIVE
    return ShortType.AGGRESSIVE


def compute_confidence(
    alignment: str,
    regime_confidence: float,
    td_anomaly: AnomalyReport,
    bu_anomaly: AnomalyReport,
) -> float:
    score = 0.70

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
) -> InvestmentRecommendation:

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
        return InvestmentRecommendation(
            action=Recommendation.SHORT,
            short_type=short_t,
            short_warning=SHORT_WARNINGS[short_t],
            confidence=confidence,
            reasoning="Bearish Signal ohne bestehende Portfolio-Position — Short möglich.",
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
        return InvestmentRecommendation(
            action=Recommendation.BUY,
            short_type=None,
            short_warning=None,
            confidence=confidence,
            reasoning="Bullish Signal ohne bestehende Portfolio-Position — Kauf empfohlen.",
        )

    return InvestmentRecommendation(
        action=Recommendation.HOLD,
        short_type=None,
        short_warning=None,
        confidence=confidence,
        reasoning="Kein klares Kauf- oder Verkaufssignal — Position halten.",
    )
