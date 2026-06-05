from typing import Optional

import yfinance as yf

from core.ports.data_provider import MarketDataProvider


class YahooFinanceProvider(MarketDataProvider):

    def get_current_price(self, ticker: str) -> Optional[float]:
        try:
            return yf.Ticker(ticker).fast_info["last_price"]
        except Exception:
            return None

    def get_price_history(self, ticker: str, period: str = "1y"):
        return yf.Ticker(ticker).history(period=period)

    def get_info(self, ticker: str) -> dict:
        try:
            return yf.Ticker(ticker).info
        except Exception:
            return {}
