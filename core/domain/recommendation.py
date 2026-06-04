from core.domain.models import (
    BottomUpResult, CockpitResult, DeepDiveResult,
    InvestmentRecommendation, Recommendation, ShortType, Signal,
)

FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}

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

ETF_ASSET_CLASSES = {"etf", "index"}
AGGRESSIVE_ASSET_CLASSES = {"equity", "precious_metal", "commodity", "bond"}


def _short_type(asset_class: str) -> ShortType:
    if asset_class.lower() in ETF_ASSET_CLASSES:
        return ShortType.DEFENSIVE
    return ShortType.AGGRESSIVE


def derive_recommendation(
    alignment: str,
    signal: Signal,
    asset_class: str,
    in_portfolio: bool,
    market: str,
    cockpit: CockpitResult,
    top_down_available: bool,
) -> InvestmentRecommendation:
    """
    Leitet BUY / HOLD / SELL / SHORT ab.
    SHORT nur wenn vollständige Analyse verfügbar (top_down + bottom_up, Markt in USA/EU/CH).
    """
    full_analysis = top_down_available and market in FULL_ANALYSIS_MARKETS
    bearish = signal == Signal.BEARISH or alignment in ("aligned_bearish", "contradicting")
    bullish = signal == Signal.BULLISH or alignment == "aligned_bullish"

    # SHORT: nur bei vollständiger Analyse, bearish Signal, NICHT im Portfolio
    if bearish and not in_portfolio and full_analysis:
        short_t = _short_type(asset_class)
        return InvestmentRecommendation(
            action=Recommendation.SHORT,
            short_type=short_t,
            short_warning=SHORT_WARNINGS[short_t],
            confidence=0.75 if alignment in ("aligned_bearish",) else 0.55,
            reasoning="Bearish Signal ohne bestehende Portfolio-Position — Short möglich.",
        )

    if bearish and in_portfolio:
        return InvestmentRecommendation(
            action=Recommendation.SELL,
            short_type=None,
            short_warning=None,
            confidence=0.80,
            reasoning="Bearish Signal bei bestehender Portfolio-Position — Verkauf empfohlen.",
        )

    if bullish and not in_portfolio:
        return InvestmentRecommendation(
            action=Recommendation.BUY,
            short_type=None,
            short_warning=None,
            confidence=0.80 if alignment == "aligned_bullish" else 0.60,
            reasoning="Bullish Signal ohne bestehende Portfolio-Position — Kauf empfohlen.",
        )

    # HOLD: bullish + im Portfolio, oder neutral
    return InvestmentRecommendation(
        action=Recommendation.HOLD,
        short_type=None,
        short_warning=None,
        confidence=0.65,
        reasoning="Kein klares Kauf- oder Verkaufssignal — Position halten.",
    )
