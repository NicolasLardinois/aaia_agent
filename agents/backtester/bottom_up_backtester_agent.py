from datetime import datetime, timezone
from typing import Callable, Optional

import yfinance as yf

from core.ports.memory_port import MemoryPort
from core.utils.backtest import (
    HORIZONS_DAYS, MIN_SAMPLE, benchmark_for_market,
    forward_return, hit_rate_ci, is_correct, market_adjusted_return,
)
from core.utils.performance_metrics import (
    apply_costs, max_drawdown, profit_factor, sharpe_ratio, sortino_ratio,
)


def _default_price_on_horizon(ticker: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
    """Erster Schlusskurs am/nach entry_date+horizon_days. None = kein Kurs (delistet)."""
    from datetime import timedelta
    target = entry_date + timedelta(days=horizon_days)
    try:
        df = yf.Ticker(ticker).history(start=target.strftime("%Y-%m-%d"), period="10d")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[0])
    except Exception:
        return None


def _default_benchmark_return(market: str, entry_date: datetime, horizon_days: int) -> Optional[float]:
    bench = benchmark_for_market(market)
    entry_px = _default_price_on_horizon(bench, entry_date, 0)
    fwd_px = _default_price_on_horizon(bench, entry_date, horizon_days)
    fr = forward_return(entry_px, fwd_px) if entry_px else None
    return fr


class BottomUpBacktesterAgent:

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

        evaluable = [
            h for h in history
            if h.get("ticker") and h.get("dominant_signal")
            and h.get("price_at_analysis") and h.get("timestamp")
        ]
        if not evaluable:
            print("[BottomUpBacktester] Keine auswertbaren Einträge — übersprungen.")
            return

        strategy_returns: list[float] = []
        correct_count = 0
        evaluated = 0

        for entry in evaluable:
            ticker     = entry["ticker"]
            price_then = float(entry["price_at_analysis"])
            signal     = entry["dominant_signal"]
            market     = entry.get("market", "USA")
            entry_date = entry["timestamp"]

            # Größtes Forward-Window wählen, dessen Periode abgeschlossen ist.
            age_days = (now - entry_date).days
            horizon = max((h for h in HORIZONS_DAYS if h <= age_days), default=None)
            if horizon is None:
                continue  # noch kein Window abgeschlossen → (noch) nicht auswertbar

            fwd_px = self.price_on_horizon(ticker, entry_date, horizon)
            raw_ret = forward_return(price_then, fwd_px)   # None nur bei ungültigem Entry
            if raw_ret is None:
                continue

            bench_ret = self.benchmark_return(market, entry_date, horizon)
            adj_ret = market_adjusted_return(raw_ret, bench_ret)
            adj_ret = apply_costs(adj_ret, self.cost_per_side)
            trade_correct = is_correct(signal, adj_ret)
            verdict = "correct" if trade_correct else "incorrect"

            if trade_correct:
                correct_count += 1

            # Strategie-Rendite: für bearish-Signale vorzeichen-spiegeln,
            # damit korrekte bearish-Calls positiv zu Sharpe/Sortino/profit_factor beitragen.
            sig_lower = (signal or "").strip().lower()
            strategy_ret = -adj_ret if sig_lower in ("bearish", "sell", "short") else adj_ret
            strategy_returns.append(strategy_ret)
            evaluated += 1

            self.memory.save_backtester_report({
                "backtester_type":        "bottomup",
                "ticker":                 ticker,
                "original_recommendation": signal,
                "price_at_recommendation": price_then,
                "price_today":            fwd_px,
                "return_pct":             round(adj_ret * 100, 2),
                "verdict":                verdict,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "notes": (
                    f"Signal={signal} | Horizont={horizon}d | "
                    f"Alpha={adj_ret * 100:.1f}% (marktbereinigt, nach Kosten)"
                ),
            })

        if evaluated >= MIN_SAMPLE:
            lo, hi = hit_rate_ci(correct_count, evaluated)
            self.memory.save_backtester_report({
                "backtester_type":        "bottomup",
                "ticker":                 None,
                "original_recommendation": None,
                "price_at_recommendation": None,
                "price_today":            None,
                "return_pct":             None,
                "verdict":                None,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "sample_size":            evaluated,
                "hit_rate":               round(correct_count / evaluated, 3),
                "hit_rate_ci_low":        lo,
                "hit_rate_ci_high":       hi,
                "sharpe":                 round(sharpe_ratio(strategy_returns, annualization=1), 3),
                "sortino":                round(sortino_ratio(strategy_returns, annualization=1), 3),
                "max_drawdown":           round(max_drawdown(strategy_returns), 3),
                "profit_factor":          round(profit_factor(strategy_returns), 3),
                "notes": (
                    f"N={evaluated} | Hit-Rate={correct_count / evaluated:.0%} "
                    f"[{lo:.0%}–{hi:.0%}] (95%-CI, marktbereinigt)"
                ),
            })

        print(f"[BottomUpBacktester] {evaluated} Einträge ausgewertet (fixes Forward-Window).")
