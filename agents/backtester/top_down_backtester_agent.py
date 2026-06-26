from datetime import datetime, timezone
from typing import Callable, Optional

from core.ports.memory_port import MemoryPort
from core.utils.backtest import HORIZONS_DAYS, hit_rate_ci, no_benchmark_return

# Regime → erwartete Richtung des realisierten Benchmark-Returns (risk-on/off).
_RISK_ON  = {"Boom", "Aufschwung", "Erholung"}
_RISK_OFF = {"Abschwung", "Rezession", "Depression"}


def _regime_expectation(regime: str) -> float:
    if regime in _RISK_ON:
        return 1.0
    if regime in _RISK_OFF:
        return -1.0
    return 0.0


def _regime_correct(regime: str, realized_return: float) -> bool:
    exp = _regime_expectation(regime)
    if exp == 0.0:
        return False
    return (exp > 0 and realized_return > 0) or (exp < 0 and realized_return < 0)


class TopDownBacktesterAgent:

    def __init__(
        self,
        memory: MemoryPort,
        benchmark_return: Optional[Callable[[str, datetime, int], Optional[float]]] = None,
    ):
        self.memory = memory
        # Benchmark-Quelle injiziert (Hexagonal §1); ohne Injektion → No-Op (kein Netz).
        self.benchmark_return = benchmark_return if benchmark_return is not None else no_benchmark_return

    async def run(self) -> None:
        history = self.memory.load_global_history(days=180)
        if not history:
            print("[TopDownBacktester] Keine Einträge — übersprungen.")
            return

        now = datetime.now(timezone.utc)
        horizon = max(HORIZONS_DAYS)  # längstes Window für die Prognoseprüfung

        entries = [
            h for h in history
            if h.get("regime") and h.get("timestamp")
            and (now - h["timestamp"]).days >= horizon
        ]
        if not entries:
            print("[TopDownBacktester] Kein abgeschlossenes Forward-Window — übersprungen.")
            return

        correct = 0
        total = 0
        for e in entries:
            regime = e["regime"]
            if _regime_expectation(regime) == 0.0:
                continue
            realized = self.benchmark_return(e.get("market", "USA"), e["timestamp"], horizon)
            if realized is None:
                continue
            total += 1
            if _regime_correct(regime, realized):
                correct += 1

        if total == 0:
            print("[TopDownBacktester] Keine bewertbaren Regime-Prognosen — übersprungen.")
            return

        accuracy = round(correct / total, 3)
        lo, hi = hit_rate_ci(correct, total)
        report = {
            "backtester_type": "topdown",
            "ticker": None,
            "original_recommendation": None,
            "price_at_recommendation": None,
            "price_today": None,
            "return_pct": None,
            "verdict": "correct" if lo >= 0.50 else "incorrect",
            "accuracy_30d": None,
            "accuracy_60d": None,
            "accuracy_90d": accuracy,
            "sample_size": total,
            "hit_rate_ci_low": lo,
            "hit_rate_ci_high": hi,
            "notes": (
                f"Prognose-Backtest (Regime t → Benchmark t+{horizon}d): "
                f"{accuracy:.0%} aus N={total} [{lo:.0%}–{hi:.0%}]"
            ),
        }
        self.memory.save_backtester_report(report)
        print(f"[TopDownBacktester] Prognosegüte {horizon}d={accuracy:.0%} "
              f"[{lo:.0%}–{hi:.0%}] | N={total}")
