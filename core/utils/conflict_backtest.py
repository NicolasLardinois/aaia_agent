"""Reine Benotungs-Mathematik für die Konflikt-Verdikte (Konflikt-Backtester).

Kein I/O. Benotet die Verdikte des Konflikt-Agenten (HOLD/EXIT/REVERSE) gegen die
Kursrealität der gehaltenen Position. Aggregation/Kennzahlen kommen wiederverwendet
aus core/utils/short_backtest.py (per-Verdikt-Buckets).
"""
from core.utils.performance_metrics import apply_costs

VALID_VERDICTS = {"HOLD", "EXIT", "REVERSE"}


def held_return(direction: str, adj_return: float) -> float:
    """Markt-bereinigtes Forward-Ergebnis der GEHALTENEN Position.

    long  → adj_return (Kursverlauf);
    short → −adj_return (ein Short gewinnt, wenn der Kurs fällt).
    direction ist per DB-Constraint immer 'long' oder 'short'.
    """
    return adj_return if direction == "long" else -adj_return


def grade_verdict(verdict: str, r: float, cost_per_side: float = 0.0005) -> tuple[bool, float]:
    """Benotet ein Verdikt gegen r (Ergebnis der gehaltenen Position) → (korrekt, Auszahlung).

    HOLD    korrekt ⟺ r > 0 (These hielt);            Auszahlung r.
    EXIT    korrekt ⟺ r < 0 (Verlust vermieden);      Auszahlung −r.
    REVERSE korrekt ⟺ Gegenposition zahlt NACH Kosten; Auszahlung apply_costs(−r)
            (strengere Latte: nicht nur „raus wäre gut", die Umkehr muss real lohnen).
    """
    if verdict == "HOLD":
        return (r > 0, r)
    if verdict == "EXIT":
        return (r < 0, -r)
    # REVERSE
    payoff = apply_costs(-r, cost_per_side)
    return (payoff > 0, payoff)
