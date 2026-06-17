import statistics

from core.domain.models import Signal
from core.utils.relative import percentile_rank

# Perzentil-Schwellen für sektor-relative Klassifikation (symmetrisch)
_CHEAP_PCTL = 30.0
_RICH_PCTL  = 70.0


def piotroski_f_score(data: dict) -> int | None:
    """Piotroski F-Score (0–9). 9 Kriterien in 3 Gruppen.
    None, falls die Pflichtfelder fehlen (kein irreführender 0-Score).

    Profitabilität (4):
      F1: roa > 0                       (positive Gesamtkapitalrendite)
      F2: operating_cash_flow > 0       (positiver operativer Cashflow)
      F3: roa > roa_prev                (ΔROA > 0, steigende Rentabilität)
      F4: operating_cash_flow > net_income  (Accruals: Qualität der Erträge)
    Leverage/Liquidität (3):
      F5: long_term_debt fällt          (sinkende Verschuldung)
      F6: current_ratio steigt          (steigende Liquidität)
      F7: keine Aktien-Verwässerung     (shares_outstanding ≤ Vorjahr)
    Operative Effizienz (2):
      F8: gross_margin steigt
      F9: asset_turnover steigt
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
    # Profitabilität (F1–F4)
    score += 1 if data["roa"] > 0 else 0                                          # F1
    score += 1 if data["operating_cash_flow"] > 0 else 0                          # F2
    score += 1 if data["roa"] > data["roa_prev"] else 0                           # F3: ΔROA > 0
    score += 1 if data["operating_cash_flow"] > data["net_income"] else 0         # F4: Accruals
    # Leverage / Liquidität (F5–F7)
    score += 1 if data["long_term_debt"] < data["long_term_debt_prev"] else 0     # F5
    score += 1 if data["current_ratio"] > data["current_ratio_prev"] else 0       # F6
    score += 1 if data["shares_outstanding"] <= data["shares_outstanding_prev"] else 0  # F7
    # Operative Effizienz (F8–F9)
    score += 1 if data["gross_margin"] > data["gross_margin_prev"] else 0         # F8
    score += 1 if data["asset_turnover"] > data["asset_turnover_prev"] else 0     # F9
    return score


def standardized_unexpected_earnings(quarters: list[dict]) -> float | None:
    """SUE = jüngste Earnings-Surprise / Std(historische Surprises).
    quarters: chronologisch, älteste zuerst (Index -1 = jüngstes Quartal), je {'actual', 'estimate'}.
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
    return surprises[-1] / std  # index -1 = jüngstes Quartal (älteste-zuerst-Konvention)


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
    Wenn loss=0 und gain=0 (komplett flache Preise), ist RSI=50 (neutral/undefiniert).
    Wenn loss=0 und gain>0 (nur steigende Preise), ist RSI=100.
    """
    try:
        delta = prices.diff().dropna()
        if len(delta) < period:
            return None
        gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
        # Flache Preise: gain=0 und loss=0 → RSI undefiniert → 50 (neutral)
        # Nur steigende Preise: gain>0 und loss=0 → RSI=100
        last_gain = float(gain.iloc[-1])
        last_loss = float(loss.iloc[-1])
        if last_loss == 0.0 and last_gain == 0.0:
            return 50.0
        loss_safe = loss.where(loss != 0, other=float("nan"))
        rs = gain / loss_safe
        rsi = (100 - (100 / (1 + rs))).fillna(100.0)
        return round(float(rsi.iloc[-1]), 2)
    except Exception:
        return None
