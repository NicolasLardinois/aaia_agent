"""Reine Kalibrierung der Risk-off-Grenze des Regime-Motors: probiert einen Composite-Bias `b`
gegen die NBER-Wahrheit (Ziel F1), per Walk-Forward (Train/Test getrennt). Kein I/O —
Kursabruf/NBER werden injiziert. Nutzt die Trend-Shift-Invarianz: jedes `b` ist aus den
gespeicherten (composite, trend) je Stichtag nachrechenbar, ohne den Replay neu zu fahren."""
from core.domain.regime import _regime_from
from core.utils.regime_eval import evaluate_nber


def bias_grid() -> list[float]:
    """1-D-Gitter der Bias-Kandidaten: -0.40 … +0.40 in 0.02-Schritten (41 Werte)."""
    return [round(-0.40 + 0.02 * i, 2) for i in range(41)]


def _confusion_for_bias(records: list, usrec_by_month: dict, b: float) -> tuple:
    """Konfusionszähler (tp, fp, fn) für einen Bias `b`: Regime via _regime_from(composite+b, trend),
    abgeglichen gegen NBER über die bestehende evaluate_nber."""
    biased = [{"as_of": d, "regime": _regime_from(c + b, t)} for (d, c, t) in records]
    nb = evaluate_nber(biased, usrec_by_month)
    return nb["tp"], nb["fp"], nb["fn"]


def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    """F1 aus Konfusionszählern; 0.0 wenn nicht definiert (keine risk-off-Calls oder keine Rezession)."""
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def f1_for_bias(records: list, usrec_by_month: dict, b: float) -> float:
    """F1 (risk-off vs. NBER-Rezession) für einen einzelnen Bias-Wert `b`."""
    tp, fp, fn = _confusion_for_bias(records, usrec_by_month, b)
    return f1_from_counts(tp, fp, fn)


def best_bias_on(records: list, usrec_by_month: dict, grid: list) -> tuple:
    """Bias mit maximalem F1 auf `records`. Tie-Break: betragskleinster Bias (Richtung Default 0)."""
    best_b, best_f1 = 0.0, -1.0
    for b in grid:
        f1 = f1_for_bias(records, usrec_by_month, b)
        if f1 > best_f1 + 1e-12 or (abs(f1 - best_f1) <= 1e-12 and abs(b) < abs(best_b)):
            best_b, best_f1 = b, f1
    return best_b, best_f1
