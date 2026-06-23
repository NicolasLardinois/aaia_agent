"""Reine Backtest-Mathematik für die Short-Entscheidungen (Shorts Block #4).

Kein I/O. Bewertet die Short-Calls (short_action) getrennt vom Long-Backtester:
gestaffelte Leih-Kosten, Einstieg-/Ausstieg-Benotung, Aufschlüsselung nach Grund,
Trefferquote vs. Profit-Faktor + Warn-Flag.
"""
from core.utils.backtest import MIN_SAMPLE, hit_rate_ci
from core.utils.performance_metrics import apply_costs, max_drawdown, profit_factor

# Leih-Miete p. a. (Dezimal) — begründete Startwerte (AGENTS.md §3):
# normal: breit verfügbare Titel ("general collateral") real ~0,3–1 %/Jahr.
BORROW_RATE_NORMAL: float = 0.01
# hard-to-borrow: real oft 5–20 %+/Jahr; 8 % als konservativer Mittelwert.
BORROW_RATE_HTB: float = 0.08


def borrow_cost(hold_days: int, hard_to_borrow: bool, manual_rate: float | None = None) -> float:
    """Anteilige Leih-Miete eines Shorts über die Haltedauer (Dezimal, ≥ 0).

    Manueller Satz schlägt den Proxy; sonst Staffel nach hard_to_borrow.
    """
    if hold_days <= 0:
        return 0.0
    if manual_rate is not None:
        rate = manual_rate
    elif hard_to_borrow:
        rate = BORROW_RATE_HTB
    else:
        rate = BORROW_RATE_NORMAL
    return rate * (hold_days / 365.0)


def grade_entry(adj_return: float, borrow: float, cost_per_side: float = 0.0005) -> tuple[bool, float]:
    """SHORT/SHORT_PLUS: korrekt, wenn die Aktie netto FIEL.

    short_payoff = -(marktbereinigter Return) - Transaktionskosten - Leih-Miete.
    Fällt die Aktie (adj < 0), ist -adj > 0 → Gewinn, minus Kosten/Borrow.
    """
    short_payoff = apply_costs(-adj_return, cost_per_side) - borrow
    return (short_payoff > 0, short_payoff)


def grade_exit(post_adj_return: float) -> tuple[bool, float]:
    """COVER: korrekt, wenn die Aktie NACH dem Cover STIEG (Verlust vermieden).

    payoff = vermiedener Verlust = marktbereinigter Return nach dem Cover.
    Keine Leih-Miete (Position ist flach), kein Round-Trip-Kostenabzug
    (kontrafaktische Mess-Größe, kein realisierter Trade).
    """
    return (post_adj_return > 0, post_adj_return)
