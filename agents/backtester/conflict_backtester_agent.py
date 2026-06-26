"""ConflictBacktesterAgent — benotet die Konflikt-Verdikte (HOLD/EXIT/REVERSE).

Geschwister zum Short-/Judgment-Backtester, anderes Prüf-Subjekt: hier zählt das
Verdikt des Konflikt-Agenten gegen die Kursrealität der gehaltenen Position. Lädt aus
dem ConflictStore, benotet, aggregiert je Verdikt-Typ. Nur messen, kein Zurückschreiben.
"""
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.conflict_store import ConflictStorePort
from core.ports.memory_port import MemoryPort
from core.utils.backtest import (
    HORIZONS_DAYS, forward_return, market_adjusted_return,
    no_benchmark_return, no_price_on_horizon,
)
from core.utils.conflict_backtest import VALID_VERDICTS, grade_verdict, held_return
from core.utils.short_backtest import aggregate_by_reason


def _parse_dt(s) -> Optional[datetime]:
    """created_at kommt aus dem ConflictStore als String → tz-aware datetime."""
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(s))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


class ConflictBacktesterAgent:
    def __init__(
        self,
        store: ConflictStorePort,
        memory: MemoryPort,
        price_on_horizon: Optional[Callable[[str, datetime, int], Optional[float]]] = None,
        benchmark_return: Optional[Callable[[str, datetime, int], Optional[float]]] = None,
        cost_per_side: float = 0.0005,
    ):
        self.store = store
        self.memory = memory
        # Kurs-/Benchmark-Quelle injiziert (Hexagonal §1); ohne Injektion → No-Op (kein Netz).
        self.price_on_horizon = price_on_horizon if price_on_horizon is not None else no_price_on_horizon
        self.benchmark_return = benchmark_return if benchmark_return is not None else no_benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        conflicts = self.store.load_for_backtest(180)
        now = datetime.now(timezone.utc)
        graded: list[dict] = []

        for c in conflicts:
            verdict = getattr(c, "verdict", None)
            ticker = getattr(c, "ticker", None)
            created = _parse_dt(getattr(c, "created_at", None))
            if verdict not in VALID_VERDICTS or not ticker or created is None:
                continue

            age_days = (now - created).days
            horizon = max((d for d in HORIZONS_DAYS if d <= age_days), default=None)
            if horizon is None:
                continue

            entry_px = self.price_on_horizon(ticker, created, 0)
            fwd_px = self.price_on_horizon(ticker, created, horizon)
            if entry_px is None:
                continue
            # fwd_px=None (delistet/insolvent) wird BEWUSST NICHT übersprungen: forward_return
            # liefert dafür -1.0 (Totalverlust, „Survivorship-Fix", wie der Long-Backtester).
            # Sonst fiele ein gehaltenes Long, das auf null ging, still weg — ein katastrophal
            # falsches HOLD würde die HOLD-Trefferquote künstlich beschönigen. Markt-Default USA.
            raw = forward_return(entry_px, fwd_px)
            if raw is None:        # greift nur noch bei entry_px <= 0 (kein gültiger Basispreis)
                continue

            bench = self.benchmark_return("USA", created, horizon)   # conflicts trägt kein market → USA
            adj = market_adjusted_return(raw, bench)
            r = held_return(getattr(c, "direction", "long"), adj)
            correct, payoff = grade_verdict(verdict, r, self.cost_per_side)
            # date=created → aggregate_by_reason sortiert die Payoffs chronologisch für den
            # reihenfolge-abhängigen Max-Drawdown (der Store lädt ORDER BY created_at DESC).
            graded.append({"archetypes": [verdict], "correct": correct,
                           "payoff": payoff, "date": created})

        for verdict, m in aggregate_by_reason(graded).items():
            self.memory.save_backtester_report({
                "backtester_type": "conflict",
                "ticker": None,
                "original_recommendation": verdict,
                "price_at_recommendation": None,
                "price_today": None,
                "return_pct": round(m["mean_payoff"] * 100, 2),
                "verdict": "WARN-payoff" if m["warning"] else None,
                "accuracy_30d": None, "accuracy_60d": None, "accuracy_90d": None,
                "notes": (f"N={m['n']} | Hit={m['hit_rate']} "
                          f"[{m['ci_low']}–{m['ci_high']}] | PF={m['profit_factor']} "
                          f"| MaxDD={m['max_drawdown']} | Warnung={m['warning']}"),
            })
        print(f"[ConflictBacktester] {len(graded)} Verdikte ausgewertet")
