from core.ports.data_provider import MarketDataProvider

# TODO: pip install yfinance
# import yfinance as yf


class YahooFinanceProvider(MarketDataProvider):
    def get_price_history(self, ticker: str, period: str = "1y") -> object:
        # TODO: return yf.Ticker(ticker).history(period=period)
        raise NotImplementedError("Yahoo Finance Adapter noch nicht implementiert")

    def get_current_price(self, ticker: str) -> float:
        # TODO: return yf.Ticker(ticker).fast_info["last_price"]
        raise NotImplementedError("Yahoo Finance Adapter noch nicht implementiert")

    def get_info(self, ticker: str) -> dict:
        # TODO: return yf.Ticker(ticker).info
        raise NotImplementedError("Yahoo Finance Adapter noch nicht implementiert")
