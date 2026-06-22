"""Reine Bewertung von Regime-Urteilen: (A) Markt-Wahrheit (Forward-S&P) und
(B) Wirtschafts-Wahrheit (NBER). Kein I/O — Kursabruf/USREC werden injiziert."""
from datetime import date

from dateutil.relativedelta import relativedelta

from core.domain.models import MarketRegime
from core.utils.backtest import forward_return, is_correct, hit_rate_ci

_BULLISH = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}


def regime_direction(regime: MarketRegime) -> str:
    """Regime → erwartete Marktrichtung. Wachstums-/Erholungsphasen bullish, Schwächephasen bearish."""
    return "bullish" if regime in _BULLISH else "bearish"


def evaluate_market(judgments: list, sp_price_on, horizons_months: tuple = (3, 6, 12)) -> dict:
    """Pro Horizont (Monate): Hit-Rate + Wilson-CI, gesamt und je Regime.
    sp_price_on(d: date) -> float | None liefert den S&P-Schlusskurs am/nach d."""
    report = {}
    for h in horizons_months:
        correct = 0
        total = 0
        by_regime: dict[str, dict] = {}
        for j in judgments:
            as_of = j["as_of"]
            regime = j["regime"]
            entry_px = sp_price_on(as_of)
            fwd_px = sp_price_on(as_of + relativedelta(months=h))
            ret = forward_return(entry_px, fwd_px)
            if ret is None:
                continue
            direction = regime_direction(regime)
            ok = is_correct(direction, ret)
            total += 1
            correct += 1 if ok else 0
            rk = regime.value
            b = by_regime.setdefault(rk, {"n": 0, "correct": 0})
            b["n"] += 1
            b["correct"] += 1 if ok else 0
        lo, hi = hit_rate_ci(correct, total)
        report[h] = {
            "n": total,
            "hit_rate": round(correct / total, 3) if total else None,
            "ci_low": lo,
            "ci_high": hi,
            "by_regime": {
                k: {"n": v["n"], "hit_rate": round(v["correct"] / v["n"], 3) if v["n"] else None}
                for k, v in by_regime.items()
            },
        }
    return report
