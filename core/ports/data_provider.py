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

    def get_real_rate_history(self, years: int = 5) -> list[dict]:
        """Datierte 10J-Realzins-Reihe (TIPS), älteste zuerst.
        Rückgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": float}, ...]; leer = nicht verfügbar.
        Default-Implementierung: leer. Echte Daten liefert der FRED-Adapter (überschreibt diese Methode)."""
        return []

    def get_policy_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []


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

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte EZB-Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []

    def get_aaa_10y_yield(self) -> Optional[float]:
        """Euro-Area AAA 10J-Nominalrendite in % (für die EU-Realzins-Berechnung:
        real = nominal − HICP). Default: None (nur der ECB-SDW-Adapter liefert echte Daten)."""
        return None


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

    def get_interest_rate_history(self, years: int = 2) -> list[dict]:
        """Datierte SNB-Leitzins-Historie [{"date","rate"}, ...]. Default: leer."""
        return []


class MarketDataProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> Optional[float]: ...

    @abstractmethod
    def get_price_history(self, ticker: str, period: str = "1y") -> object: ...

    @abstractmethod
    def get_info(self, ticker: str) -> dict: ...

    def get_index_constituents(self, index_ticker: str) -> list[str]:
        """Konstituenten-Ticker des Index; leer = unbekannt."""
        return []

    def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
        """{ticker: Close-pandas.Series} der Konstituenten; leer = unbekannt."""
        return {}

    def get_index_fundamentals(self, index_ticker: str) -> dict:
        """Aggregierte (bottom-up) Index-Fundamentaldaten:
        {"eps_ttm","eps_fwd","eps_growth_1y","revenue_growth_1y","operating_margin",
         "estimate_revision": "up"|"stable"|"down"}; leeres dict = nicht verfügbar.
        Default-Implementierung: leer. Echte Daten liefert ein spezialisierter Adapter."""
        return {}

    def get_index_holdings(self, index_ticker: str) -> list:
        """[{"name": str, "weight_pct": float, "sector": str}], absteigend nach Gewicht;
        leer = nicht verfügbar.
        Default-Implementierung: leer. Echte Daten liefert ein spezialisierter Adapter."""
        return []


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


class CommoditySupplyProvider(ABC):
    @abstractmethod
    def get_inventory_history(self, commodity: str, years: int = 5) -> list[dict]:
        """[{"date": "YYYY-MM-DD", "inventory": float}], älteste zuerst; leer = nicht verfügbar."""
        ...

    @abstractmethod
    def get_production_cost_curve(self, commodity: str) -> dict:
        """{"cost_p25","cost_p50","cost_p75","cost_p90"} in Preiseinheit des Tickers; leer = nicht verfügbar."""
        ...


class COTProvider(ABC):
    @abstractmethod
    def get_cot_history(self, commodity: str, years: int = 3) -> list[dict]:
        """[{"date","managed_money_net","open_interest"}], älteste zuerst; leer = nicht verfügbar."""
        ...


class SentimentDataProvider(ABC):
    @abstractmethod
    def get_fear_greed(self) -> Optional[float]:
        """Aktueller CNN-Fear&Greed-Wert 0–100; None = nicht verfügbar."""
        ...
