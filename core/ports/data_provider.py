from abc import ABC, abstractmethod
from typing import Optional


class MacroDataProvider(ABC):
    @abstractmethod
    def get_economic_state(self) -> dict[str, float]: ...

    @abstractmethod
    def get_extended_state(self) -> dict[str, float]: ...


class EcbDataProvider(ABC):
    @abstractmethod
    def get_interest_rate(self) -> Optional[float]: ...

    @abstractmethod
    def get_m3_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_balance_sheet_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_cpi(self) -> Optional[float]: ...

    @abstractmethod
    def get_core_cpi(self) -> Optional[float]: ...

    @abstractmethod
    def get_ppi(self) -> Optional[float]: ...

    @abstractmethod
    def get_gdp_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_unemployment(self) -> Optional[float]: ...

    @abstractmethod
    def get_pmi(self) -> Optional[float]: ...

    @abstractmethod
    def get_m2_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_sovereign_yields(self) -> dict[str, Optional[float]]:
        """Returns yields for DE, IT, FR, ES 10Y bonds."""
        ...


class SnbDataProvider(ABC):
    @abstractmethod
    def get_interest_rate(self) -> Optional[float]: ...

    @abstractmethod
    def get_m3_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_balance_sheet_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_cpi(self) -> Optional[float]: ...

    @abstractmethod
    def get_core_cpi(self) -> Optional[float]: ...

    @abstractmethod
    def get_gdp_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_unemployment(self) -> Optional[float]: ...

    @abstractmethod
    def get_m2_growth(self) -> Optional[float]: ...

    @abstractmethod
    def get_sovereign_yield_10y(self) -> Optional[float]: ...

    @abstractmethod
    def get_sovereign_yield_2y(self) -> Optional[float]: ...


class MarketDataProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> Optional[float]: ...

    @abstractmethod
    def get_price_history(self, ticker: str, period: str = "1y") -> object: ...

    @abstractmethod
    def get_info(self, ticker: str) -> dict: ...


class FundamentalsProvider(ABC):
    @abstractmethod
    def get_fundamentals(self, ticker: str) -> dict: ...

    @abstractmethod
    def get_short_interest(self, ticker: str) -> dict: ...

    @abstractmethod
    def get_insider_activity(self, ticker: str) -> list[dict]: ...

    @abstractmethod
    def get_earnings_history(self, ticker: str) -> list[dict]: ...

    @abstractmethod
    def get_bond_data(self, ticker: str) -> dict: ...


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> str: ...
