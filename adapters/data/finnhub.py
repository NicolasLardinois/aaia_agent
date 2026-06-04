from core.ports.data_provider import FundamentalsProvider

# TODO: pip install finnhub-python
# import finnhub


class FinnhubProvider(FundamentalsProvider):
    def __init__(self, api_key: str):
        # TODO: self.client = finnhub.Client(api_key=api_key)
        self.api_key = api_key

    def get_fundamentals(self, ticker: str) -> dict:
        # TODO: Implementierung mit finnhub
        raise NotImplementedError("Finnhub Adapter noch nicht implementiert")

    def get_short_interest(self, ticker: str) -> dict:
        # TODO: Alternativ: Financial Modeling Prep API
        raise NotImplementedError("Finnhub Adapter noch nicht implementiert")

    def get_insider_activity(self, ticker: str) -> list[dict]:
        # TODO: self.client.stock_insider_transactions(ticker)
        raise NotImplementedError("Finnhub Adapter noch nicht implementiert")

    def get_earnings_history(self, ticker: str) -> list[dict]:
        # TODO: self.client.company_earnings(ticker, limit=4)
        raise NotImplementedError("Finnhub Adapter noch nicht implementiert")
