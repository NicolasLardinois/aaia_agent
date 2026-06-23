"""ShortBacktesterAgent — benotet die Short-Entscheidungen (short_action) getrennt.

Geschwister zum JudgmentBacktesterAgent, anderes Prüf-Subjekt: hier zählt die
Trade-Entscheidung des Short-Motors (Einstieg SHORT/SHORT+, Ausstieg COVER) —
mit Leih-Kosten, aufgeschlüsselt nach Grund. Nur messen, kein Zurückschreiben.
"""
import json
from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.memory_port import MemoryPort
from core.utils.backtest import HORIZONS_DAYS, forward_return, market_adjusted_return
from core.utils.short_backtest import (
    aggregate_by_reason, borrow_cost, grade_entry, grade_exit,
)
from agents.backtester.bottom_up_backtester_agent import (
    _default_benchmark_return, _default_price_on_horizon,
)

_ENTRY_ACTIONS = {"SHORT", "SHORT+"}
_EXIT_ACTIONS = {"COVER"}
_SHORT_ACTIONS = _ENTRY_ACTIONS | _EXIT_ACTIONS


def _parse_meta(raw) -> dict:
    """short_meta kommt als dict (psycopg2-jsonb) oder str — defensiv beides."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    return {}


class ShortBacktesterAgent:
    def __init__(
        self,
        memory: MemoryPort,
        price_on_horizon: Callable[[str, datetime, int], Optional[float]] = _default_price_on_horizon,
        benchmark_return: Callable[[str, datetime, int], Optional[float]] = _default_benchmark_return,
        cost_per_side: float = 0.0005,
    ):
        self.memory = memory
        self.price_on_horizon = price_on_horizon
        self.benchmark_return = benchmark_return
        self.cost_per_side = cost_per_side

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        now = datetime.now(timezone.utc)
        entries: list[dict] = []
        exits: list[dict] = []

        for h in history:
            action = h.get("short_action")
            ticker = h.get("ticker")
            price_then = h.get("price_at_analysis")
            entry_date = h.get("timestamp")
            if not (ticker and price_then and entry_date
                    and action in _SHORT_ACTIONS):
                continue

            age_days = (now - entry_date).days
            horizon = max((d for d in HORIZONS_DAYS if d <= age_days), default=None)
            if horizon is None:
                continue

            fwd_px = self.price_on_horizon(ticker, entry_date, horizon)
            # Kein Folgekurs → Daten fehlen noch, nicht auswertbar (defensiv überspringen).
            # Hinweis: forward_return(px, None) = -1.0 (Survivorship-Fix), aber hier
            # bedeutet None «Preis noch nicht verfügbar» — daher explizit überspringen.
            if fwd_px is None:
                continue
            raw = forward_return(float(price_then), fwd_px)
            if raw is None:
                continue
            bench = self.benchmark_return(h.get("market", "USA"), entry_date, horizon)
            adj = market_adjusted_return(raw, bench)

            meta = _parse_meta(h.get("short_meta"))
            archetypes = meta.get("archetypes") or []

            if action in _ENTRY_ACTIONS:
                borrow = borrow_cost(horizon, bool(meta.get("hard_to_borrow")),
                                     meta.get("borrow_rate_manual"))
                correct, payoff = grade_entry(adj, borrow, self.cost_per_side)
                entries.append({"archetypes": archetypes, "correct": correct, "payoff": payoff})
            else:  # COVER
                correct, payoff = grade_exit(adj)
                exits.append({"archetypes": archetypes, "correct": correct, "payoff": payoff})

        self._save_section("entry", aggregate_by_reason(entries))
        self._save_section("exit", aggregate_by_reason(exits))
        print(f"[ShortBacktester] Einstiege: {len(entries)} | Ausstiege: {len(exits)}")

    def _save_section(self, section: str, buckets: dict) -> None:
        for reason, m in buckets.items():
            self.memory.save_backtester_report({
                "backtester_type": "short",
                "ticker": None,
                "original_recommendation": f"{section}:{reason}",
                "price_at_recommendation": None,
                "price_today": None,
                "return_pct": round(m["mean_payoff"] * 100, 2),
                "verdict": "WARN-payoff" if m["warning"] else None,
                "accuracy_30d": None, "accuracy_60d": None, "accuracy_90d": None,
                "notes": (f"N={m['n']} | Hit={m['hit_rate']} "
                          f"[{m['ci_low']}–{m['ci_high']}] | PF={m['profit_factor']} "
                          f"| MaxDD={m['max_drawdown']} | Warnung={m['warning']}"),
            })
