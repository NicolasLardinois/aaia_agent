from typing import Optional
import yfinance as yf
from core.ports.memory_port import MemoryPort


def _fetch_price(ticker: str) -> Optional[float]:
    try:
        return float(yf.Ticker(ticker).fast_info["last_price"])
    except Exception:
        return None


def _verdict(signal: str, return_pct: float) -> str:
    if signal == "bullish" and return_pct >= 2.0:
        return "correct"
    if signal == "bearish" and return_pct <= -2.0:
        return "correct"
    if signal == "neutral" and abs(return_pct) <= 2.0:
        return "correct"
    if abs(return_pct) <= 1.0:
        return "neutral"
    return "incorrect"


class BottomUpBacktesterAgent:

    def __init__(self, memory: MemoryPort):
        self.memory = memory

    async def run(self) -> None:
        history = self.memory.load_global_history(days=90)
        evaluable = [
            h for h in history
            if h.get("ticker") and h.get("dominant_signal") and h.get("price_at_analysis")
        ]
        if not evaluable:
            print("[BottomUpBacktester] Keine auswertbaren Einträge — übersprungen.")
            return

        evaluated = 0
        for entry in evaluable:
            ticker     = entry["ticker"]
            price_then = float(entry["price_at_analysis"])
            signal     = entry["dominant_signal"]

            price_now = _fetch_price(ticker)
            if price_now is None:
                continue

            return_pct = ((price_now - price_then) / price_then) * 100
            verdict    = _verdict(signal, return_pct)

            self.memory.save_backtester_report({
                "backtester_type":        "bottomup",
                "ticker":                 ticker,
                "original_recommendation": signal,
                "price_at_recommendation": price_then,
                "price_today":            price_now,
                "return_pct":             round(return_pct, 2),
                "verdict":                verdict,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "notes": f"Signal={signal} | Return={return_pct:.1f}%",
            })
            evaluated += 1

        print(f"[BottomUpBacktester] {evaluated} Einträge ausgewertet.")
