import statistics

from core.domain.models import Signal
from core.utils.relative import percentile_rank

# Perzentil-Schwellen für sektor-relative Klassifikation (symmetrisch)
_CHEAP_PCTL = 30.0
_RICH_PCTL  = 70.0


def piotroski_f_score(data: dict) -> int | None:
    """Piotroski F-Score (0–9). 9 Kriterien in 3 Gruppen.
    None, falls die Pflichtfelder fehlen (kein irreführender 0-Score).

    Profitabilität (4): net_income>0; roa>0; operating_cash_flow>0; OCF>net_income (Accruals).
    Leverage/Liquidität (3): long_term_debt fällt; current_ratio steigt; keine Aktien-Verwässerung.
    Operative Effizienz (2): gross_margin steigt; asset_turnover steigt.
    """
    required = (
        "net_income", "roa", "operating_cash_flow", "roa_prev",
        "long_term_debt", "long_term_debt_prev",
        "current_ratio", "current_ratio_prev",
        "shares_outstanding", "shares_outstanding_prev",
        "gross_margin", "gross_margin_prev",
        "asset_turnover", "asset_turnover_prev",
    )
    if any(data.get(k) is None for k in required):
        return None

    score = 0
    # Profitabilität
    score += 1 if data["net_income"] > 0 else 0
    score += 1 if data["roa"] > 0 else 0
    score += 1 if data["operating_cash_flow"] > 0 else 0
    score += 1 if data["operating_cash_flow"] > data["net_income"] else 0
    # Leverage / Liquidität
    score += 1 if data["long_term_debt"] < data["long_term_debt_prev"] else 0
    score += 1 if data["current_ratio"] > data["current_ratio_prev"] else 0
    score += 1 if data["shares_outstanding"] <= data["shares_outstanding_prev"] else 0
    # Operative Effizienz
    score += 1 if data["gross_margin"] > data["gross_margin_prev"] else 0
    score += 1 if data["asset_turnover"] > data["asset_turnover_prev"] else 0
    return score


def standardized_unexpected_earnings(quarters: list[dict]) -> float | None:
    """SUE = jüngste Earnings-Surprise / Std(historische Surprises).
    quarters: neueste zuerst (Index 0 = jüngstes Quartal), je {'actual', 'estimate'}.
    None bei <4 Quartalen oder Std==0. Misst die Magnitude statt nur Beat/Miss.
    """
    surprises = [
        q["actual"] - q["estimate"]
        for q in quarters
        if q.get("actual") is not None and q.get("estimate") is not None
    ]
    if len(surprises) < 4:
        return None
    std = statistics.stdev(surprises)
    if std == 0.0:
        return None
    return surprises[0] / std  # index 0 = jüngstes Quartal


def sector_relative_signal(value: float, sector_history: list[float],
                           lower_is_better: bool) -> Signal:
    """Klassifiziert `value` relativ zur Sektor-Verteilung über den Perzentil-Rang
    (Plan-0 `percentile_rank`). NEUTRAL bei leerer Historie.

    lower_is_better=True (Bewertungs-Multiples wie P/E): niedriges Perzentil = günstig = BULLISH.
    lower_is_better=False (Qualität wie Marge): hohes Perzentil = stark = BULLISH.
    """
    pctl = percentile_rank(value, sector_history)
    if pctl is None:
        return Signal.NEUTRAL
    cheap = pctl <= _CHEAP_PCTL
    rich  = pctl >= _RICH_PCTL
    if lower_is_better:
        if cheap:
            return Signal.BULLISH
        if rich:
            return Signal.BEARISH
    else:
        if rich:
            return Signal.BULLISH
        if cheap:
            return Signal.BEARISH
    return Signal.NEUTRAL


def wilder_rsi(prices, period: int = 14) -> float | None:
    """RSI nach Wilder (ewm alpha=1/period, adjust=False) statt SMA (Cutler).
    Erwartet eine pandas-Series. None bei Fehler / zu kurzer Historie.
    Wenn loss=0 (nur steigende Preise), ist RSI=100.
    """
    try:
        delta = prices.diff().dropna()
        if len(delta) < period:
            return None
        gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
        # Wenn loss=0 → RS ist unendlich → RSI=100; NaN-Werte durch 100 ersetzen
        loss_safe = loss.where(loss != 0, other=float("nan"))
        rs = gain / loss_safe
        rsi = (100 - (100 / (1 + rs))).fillna(100.0)
        return round(float(rsi.iloc[-1]), 2)
    except Exception:
        return None
