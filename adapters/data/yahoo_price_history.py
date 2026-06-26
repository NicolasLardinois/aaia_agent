"""Yahoo-Finance-Adapter für die historische Kursquelle der Backtester.

Kapselt das blockierende `yfinance`-I/O, das früher direkt im Agent-Modul
`bottom_up_backtester_agent` stand (`_default_price_on_horizon`). Defensiver
Vertrag (AGENTS.md §2/§3): kein Kurs/Exception → `None` (Survivorship-Behandlung
übernimmt der reine `forward_return`-Helfer im Kern).
"""
from datetime import datetime, timedelta

import yfinance as yf

from core.ports.price_history import PriceHistoryProvider


class YahooPriceHistoryProvider(PriceHistoryProvider):
    def get_price_on_horizon(
        self, ticker: str, entry_date: datetime, horizon_days: int
    ) -> float | None:
        """Erster Schlusskurs am/nach entry_date+horizon_days. None = kein Kurs (delistet)."""
        target = entry_date + timedelta(days=horizon_days)
        try:
            df = yf.Ticker(ticker).history(start=target.strftime("%Y-%m-%d"), period="10d")
            if df is None or df.empty:
                return None
            return float(df["Close"].iloc[0])
        except Exception:
            return None
