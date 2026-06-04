from core.ports.memory_port import MemoryPort

REGIME_CYCLE = ["Boom", "Aufschwung", "Erholung", "Abschwung", "Rezession"]

_ADJACENT: dict[str, set] = {
    r: {
        REGIME_CYCLE[max(0, i - 1)],
        r,
        REGIME_CYCLE[min(len(REGIME_CYCLE) - 1, i + 1)],
    }
    for i, r in enumerate(REGIME_CYCLE)
}


def _is_adjacent(a: str, b: str) -> bool:
    return b in _ADJACENT.get(a, {a})


def _accuracy(entries: list[dict], reference_regime: str) -> float:
    if not entries:
        return 0.0
    correct = sum(1 for e in entries if _is_adjacent(e["regime"], reference_regime))
    return round(correct / len(entries), 3)


class TopDownBacktesterAgent:

    def __init__(self, memory: MemoryPort):
        self.memory = memory

    async def run(self) -> None:
        history = self.memory.load_global_history(days=90)
        if not history:
            print("[TopDownBacktester] Keine Einträge — übersprungen.")
            return

        latest = max(history, key=lambda h: h["timestamp"])
        ref_regime = latest.get("regime")
        if not ref_regime:
            print("[TopDownBacktester] Kein Regime im letzten Eintrag — übersprungen.")
            return

        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        def entries_in_window(days: int) -> list[dict]:
            cutoff = now - timedelta(days=days)
            return [
                h for h in history
                if h.get("regime") and h["timestamp"] >= cutoff
            ]

        e30 = entries_in_window(30)
        e60 = entries_in_window(60)
        e90 = entries_in_window(90)

        acc30 = _accuracy(e30, ref_regime)
        acc60 = _accuracy(e60, ref_regime)
        acc90 = _accuracy(e90, ref_regime)

        report = {
            "backtester_type": "topdown",
            "ticker": None,
            "original_recommendation": None,
            "price_at_recommendation": None,
            "price_today": None,
            "return_pct": None,
            "verdict": "correct" if acc30 >= 0.70 else "incorrect",
            "accuracy_30d": acc30,
            "accuracy_60d": acc60,
            "accuracy_90d": acc90,
            "notes": (
                f"Referenz-Regime: {ref_regime}. "
                f"Treffsicherheit 30d={acc30:.0%} 60d={acc60:.0%} 90d={acc90:.0%}"
            ),
        }
        self.memory.save_backtester_report(report)
        print(f"[TopDownBacktester] Treffsicherheit 30d={acc30:.0%} | Regime: {ref_regime}")
