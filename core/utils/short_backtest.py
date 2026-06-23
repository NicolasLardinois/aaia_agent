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


PAYOFF_WARN_HIT_RATE: float = 0.55       # "oft recht"
PAYOFF_WARN_PROFIT_FACTOR: float = 1.0   # aber unterm Strich Verlust
_NO_REASON = "(ohne Grund)"


def payoff_warning(hit_rate: float | None, pf: float) -> bool:
    """True, wenn oft recht (≥ 55 %) ABER Profit-Faktor < 1 (Squeeze-Asymmetrie).

    Gibt an, dass ein Archetyp eine hohe Trefferquote hat, aber die Durchschnittsverluste
    die Durchschnittsgewinne übersteigen → Asymmetrie zwischen Häufigkeit und Betrag.
    """
    if hit_rate is None:
        return False
    return hit_rate >= PAYOFF_WARN_HIT_RATE and pf < PAYOFF_WARN_PROFIT_FACTOR


def aggregate_by_reason(graded: list[dict]) -> dict[str, dict]:
    """Je Short-Grund (Archetyp) ein Bucket mit Kennzahlen.

    Ein Eintrag mit mehreren Archetypen zählt in JEDEN zugehörigen Bucket;
    leere Archetypen → Bucket "(ohne Grund)". Trefferquote erst ab MIN_SAMPLE.

    graded: Liste von {"archetypes": list[str], "correct": bool, "payoff": float,
            optional "date": datetime}. Trägt jeder Eintrag ein "date", werden die
            Payoffs je Bucket chronologisch (alt→neu) sortiert, bevor der Max-Drawdown
            gerechnet wird — sonst hinge der Drawdown von der Einlese-Reihenfolge ab
            (Trefferquote/Mittel/Profit-Faktor sind reihenfolge-unabhängig).
    out: dict[str, dict] mit Schlüsseln "n", "hit_rate", "ci_low", "ci_high",
         "mean_payoff", "profit_factor", "max_drawdown", "warning".
    """
    buckets: dict[str, list[dict]] = {}
    for g in graded:
        for reason in (g.get("archetypes") or [_NO_REASON]):
            buckets.setdefault(reason, []).append(g)

    out: dict[str, dict] = {}
    for reason, items in buckets.items():
        # Max-Drawdown ist reihenfolge-abhängig → chronologisch ordnen, wenn Datum da ist.
        # Ohne Datum (z. B. reine Funktions-Tests) bleibt die Einlese-Reihenfolge stabil.
        if all(it.get("date") is not None for it in items):
            items = sorted(items, key=lambda it: it["date"])
        n = len(items)
        payoffs = [it["payoff"] for it in items]
        correct = sum(1 for it in items if it["correct"])
        if n >= MIN_SAMPLE:
            hit = round(correct / n, 3)
            lo, hi = hit_rate_ci(correct, n)
        else:
            hit, lo, hi = None, None, None
        pf = profit_factor(payoffs)   # kann float("inf") sein (keine Verluste)
        out[reason] = {
            "n": n,
            "hit_rate": hit,
            "ci_low": lo,
            "ci_high": hi,
            "mean_payoff": round(sum(payoffs) / n, 4) if n else 0.0,
            "profit_factor": None if pf == float("inf") else round(pf, 3),
            "max_drawdown": round(max_drawdown(payoffs), 3),
            "warning": payoff_warning(hit, pf),
        }
    return out
