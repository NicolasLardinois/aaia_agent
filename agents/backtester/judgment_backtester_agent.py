from typing import Optional
import yfinance as yf
from core.ports.memory_port import MemoryPort


def _fetch_price(ticker: str) -> Optional[float]:
    try:
        return float(yf.Ticker(ticker).fast_info["last_price"])
    except Exception:
        return None


def _verdict(recommendation: str, return_pct: float) -> str:
    if recommendation == "BUY"  and return_pct >= 3.0:
        return "correct"
    if recommendation in ("SELL", "SHORT") and return_pct <= -3.0:
        return "correct"
    if recommendation == "HOLD" and abs(return_pct) <= 5.0:
        return "correct"
    if abs(return_pct) <= 1.5:
        return "neutral"
    return "incorrect"


class JudgmentBacktesterAgent:

    def __init__(self, memory: MemoryPort):
        self.memory = memory

    async def run(self) -> None:
        history = self.memory.load_global_history(days=90)
        evaluable = [
            h for h in history
            if h.get("ticker") and h.get("recommendation") and h.get("price_at_analysis")
        ]
        if not evaluable:
            print("[JudgmentBacktester] Keine auswertbaren Einträge — übersprungen.")
            return

        correct = 0
        total   = 0

        for entry in evaluable:
            ticker     = entry["ticker"]
            price_then = float(entry["price_at_analysis"])
            rec        = entry["recommendation"]

            price_now = _fetch_price(ticker)
            if price_now is None:
                continue

            return_pct = ((price_now - price_then) / price_then) * 100
            verdict    = _verdict(rec, return_pct)

            if verdict == "correct":
                correct += 1
            total += 1

            self.memory.save_backtester_report({
                "backtester_type":        "judgment",
                "ticker":                 ticker,
                "original_recommendation": rec,
                "price_at_recommendation": price_then,
                "price_today":            price_now,
                "return_pct":             round(return_pct, 2),
                "verdict":                verdict,
                "accuracy_30d":           None,
                "accuracy_60d":           None,
                "accuracy_90d":           None,
                "notes": f"Empfehlung={rec} | Return={return_pct:.1f}% | Urteil={verdict}",
            })

        if total > 0:
            accuracy = round(correct / total, 3)
            self.memory.save_backtester_report({
                "backtester_type":        "judgment",
                "ticker":                 None,
                "original_recommendation": None,
                "price_at_recommendation": None,
                "price_today":            None,
                "return_pct":             None,
                "verdict": "correct" if accuracy >= 0.60 else "incorrect",
                "accuracy_30d":  accuracy,
                "accuracy_60d":  None,
                "accuracy_90d":  None,
                "notes": f"Gesamttreffsicherheit: {accuracy:.0%} aus {total} Empfehlungen",
            })
            print(f"[JudgmentBacktester] {total} ausgewertet | Treffsicherheit: {accuracy:.0%}")
