"""Yahoo-Finance-Adapter für Live-Kurse + Wechselkurse (Portfolio-Monitor).

Kapselt das blockierende `yfinance`-I/O, das früher direkt im Agenten stand
(`_fetch_current_price` / `_default_fx_rate`). Defensiver Vertrag (AGENTS.md §2/§3):
ein fehlgeschlagener Call darf die Portfolio-Analyse nie abstürzen lassen → Kurs
fällt auf `None`, FX auf `1.0` zurück.
"""
import yfinance as yf

from core.ports.live_price import LivePriceProvider


class YahooLivePriceProvider(LivePriceProvider):
    def get_current_price(self, ticker: str) -> float | None:
        try:
            return float(yf.Ticker(ticker).fast_info["last_price"])
        except Exception:
            return None

    def get_fx_rate(self, from_ccy: str, to_ccy: str) -> float:
        if from_ccy == to_ccy:
            return 1.0
        try:
            # Yahoo-FX-Symbol, z. B. "CHFUSD=X" → CHF in USD.
            px = yf.Ticker(f"{from_ccy}{to_ccy}=X").fast_info["last_price"]
            return float(px) if px else 1.0
        except Exception:
            return 1.0
