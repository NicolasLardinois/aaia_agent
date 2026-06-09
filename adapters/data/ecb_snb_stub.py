"""
Stub-Adapter für ECB und SNB.
Alle Methoden geben None zurück bis die echten APIs angebunden sind.

TODO: ECB Statistical Data Warehouse (SDW) API
TODO: SNB data.snb.ch API
TODO: Eurostat API für EU-Makrodaten
"""
from typing import Optional
from core.ports.data_provider import EcbDataProvider, SnbDataProvider


class EcbStubProvider(EcbDataProvider):
    def get_interest_rate(self) -> Optional[float]:         return None  # TODO: ECB SDW
    def get_m3_growth(self) -> Optional[float]:             return None  # TODO: ECB SDW
    def get_balance_sheet_growth(self) -> Optional[float]:  return None  # TODO: ECB SDW
    def get_cpi(self) -> Optional[float]:                   return None  # TODO: Eurostat
    def get_core_cpi(self) -> Optional[float]:              return None  # TODO: Eurostat
    def get_ppi(self) -> Optional[float]:                   return None  # TODO: Eurostat
    def get_gdp_growth(self) -> Optional[float]:            return None  # TODO: Eurostat
    def get_unemployment(self) -> Optional[float]:          return None  # TODO: Eurostat
    def get_pmi(self) -> Optional[float]:                   return None  # TODO: S&P Global
    def get_m2_growth(self) -> Optional[float]:             return None  # TODO: ECB SDW
    def get_sovereign_yields(self) -> dict[str, Optional[float]]:
        return {"DE_10y": None, "IT_10y": None, "FR_10y": None, "ES_10y": None}  # TODO
    def get_yield_spreads(self) -> dict[str, float | None]:
        return {"10y2y": None, "10y3m": None}


class SnbStubProvider(SnbDataProvider):
    def get_interest_rate(self) -> Optional[float]:         return None  # TODO: data.snb.ch
    def get_m3_growth(self) -> Optional[float]:             return None  # TODO: data.snb.ch
    def get_balance_sheet_growth(self) -> Optional[float]:  return None  # TODO: data.snb.ch
    def get_cpi(self) -> Optional[float]:                   return None  # TODO: BFS
    def get_core_cpi(self) -> Optional[float]:              return None  # TODO: BFS
    def get_gdp_growth(self) -> Optional[float]:            return None  # TODO: SECO
    def get_unemployment(self) -> Optional[float]:          return None  # TODO: SECO
    def get_m2_growth(self) -> Optional[float]:             return None  # TODO: data.snb.ch
    def get_sovereign_yield_10y(self) -> Optional[float]:   return None  # TODO: Yahoo/SNB
    def get_sovereign_yield_2y(self) -> Optional[float]:    return None  # TODO: Yahoo/SNB
    def get_yield_spreads(self) -> dict[str, float | None]:
        return {"10y3m": None}
