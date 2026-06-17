from abc import ABC, abstractmethod
from typing import Optional


class MacroDataProvider(ABC):
    @abstractmethod
    def get_economic_state(self) -> dict[str, float]: ...

    @abstractmethod
    def get_extended_state(self) -> dict[str, float]: ...

    @abstractmethod
    def get_buffett_data(self) -> dict[str, float]: ...

    @abstractmethod
    def get_buffett_history(self, years: int = 10) -> list[float]: ...
    """Gibt quartalsweise Buffett-Quoten (%) der letzten N Jahre zurück, älteste zuerst."""

    @abstractmethod
    def get_yield_spreads(self) -> dict[str, float | None]:
        """USA 10y-2y und 10y-3m Treasury Spreads. Keys: '10y2y', '10y3m'."""
        ...

    @abstractmethod
    def get_real_rate_history(self, years: int = 5) -> list[dict]:
        """Datierte 10J-Realzins-Reihe (TIPS), älteste zuerst.
        Rückgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": float}, ...]; leer = nicht verfügbar."""
        ...


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

    @abstractmethod
    def get_yield_spreads(self) -> dict[str, float | None]:
        """Eurozone AAA 10y-2y und 10y-3m Spreads. Keys: '10y2y', '10y3m'."""
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

    @abstractmethod
    def get_yield_spreads(self) -> dict[str, float | None]:
        """CH 10y-3m Spread (kein 2y verfügbar). Key: '10y3m'."""
        ...


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
