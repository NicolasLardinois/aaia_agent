from datetime import date

import numpy as np
import pandas as pd
from fredapi import Fred

from core.ports.data_provider import MacroDataProvider
from adapters.data.fred_api import SERIES, EXTENDED_SERIES


def _default_series_loader(fred: Fred, series_id: str, as_of: date) -> pd.Series:
    """Point-in-Time-Serie: bevorzugt Vintage (Stand wie am `as_of` veröffentlicht),
    sonst Rückfall auf die revidierte Serie, in beiden Fällen auf Datum <= as_of geschnitten.
    Setzt das Attribut NICHT — die Qualität ermittelt der Aufrufer über _has_vintage."""
    ts = pd.Timestamp(as_of)
    try:
        # get_series_as_of_date liefert die zum Stichtag bekannten Releases
        df = fred.get_series_as_of_date(series_id, as_of)
        # Normalisieren auf observation_date -> letzter bekannter value je Datum
        df = df[["date", "value"]].copy()
        df["date"] = pd.to_datetime(df["date"])
        s = df.dropna().groupby("date")["value"].last()
        s = s[s.index <= ts].astype(float)
        if not s.empty:
            return s
    except Exception:
        pass
    # Fallback: revidierte Serie, auf <= as_of geschnitten
    s = fred.get_series(series_id)
    s.index = pd.to_datetime(s.index)
    return s[s.index <= ts].astype(float)


class HistoricalFredProvider(MacroDataProvider):
    """Wie FredDataProvider, aber Point-in-Time zum Stichtag `as_of`. Nutzt dieselben
    Serien-Mappings/Transformationen, damit der Regime-Input identisch zum Live-Pfad ist."""

    def __init__(self, api_key: str, as_of: date, _series_loader=None):
        self.as_of = as_of
        self.quality = "unbekannt"
        self._fred = Fred(api_key=api_key) if _series_loader is None else None
        self._load = _series_loader or _default_series_loader

    def _series(self, series_id: str) -> pd.Series:
        return self._load(self._fred, series_id, self.as_of)

    def _state_from(self, mapping: dict) -> dict:
        state = {}
        for key, (fred_id, transform) in mapping.items():
            try:
                data = self._series(fred_id)
                value = float(transform(data))
                state[key] = round(value, 3) if not np.isnan(value) else None
            except Exception:
                state[key] = None
        return state

    def get_economic_state(self) -> dict:
        state = self._state_from(SERIES)
        # Qualitäts-Flag grob über die Kern-Reihe CPIAUCSL bestimmen
        try:
            self.quality = "vintage" if self._has_vintage("CPIAUCSL") else "revised"
        except Exception:
            self.quality = "revised"
        return state

    def get_extended_state(self) -> dict:
        state = self._state_from(EXTENDED_SERIES)
        nom = state.get("nominal_wage_growth")
        try:
            cpi = self._series("CPIAUCSL")
            inf_val = float(cpi.pct_change(12).dropna().iloc[-1] * 100)
            inf = round(inf_val, 3) if not np.isnan(inf_val) else None
        except Exception:
            inf = None
        if nom is not None and inf is not None:
            state["real_wage_growth"] = round(nom - inf, 3)
        return state

    def get_yield_spreads(self) -> dict:
        result = {"10y2y": None, "10y3m": None}
        for key, fred_id in (("10y2y", "T10Y2Y"), ("10y3m", "T10Y3M")):
            try:
                s = self._series(fred_id)
                result[key] = round(float(s.dropna().iloc[-1]), 3)
            except Exception:
                pass
        return result

    def get_buffett_data(self) -> dict:
        try:
            market_cap = float(self._series("WILL5000INDFC").dropna().iloc[-1])
            gdp        = float(self._series("GDP").dropna().iloc[-1])
            return {"market_cap_bn": market_cap, "gdp_bn": gdp}
        except Exception:
            return {"market_cap_bn": None, "gdp_bn": None}

    def get_buffett_history(self, years: int = 10) -> list:
        try:
            wilshire = self._series("WILL5000INDFC").resample("Q").last().dropna()
            gdp      = self._series("GDP").resample("Q").last().dropna()
            aligned  = wilshire.align(gdp, join="inner")
            ratios   = (aligned[0] / aligned[1] * 100).dropna()
            cutoff   = pd.Timestamp(self.as_of) - pd.DateOffset(years=years)
            ratios   = ratios[ratios.index >= cutoff]
            return [round(float(r), 1) for r in ratios]
        except Exception:
            return []

    def _has_vintage(self, series_id: str) -> bool:
        """True, wenn FRED für series_id einen echten Vintage-Stand zum as_of liefert."""
        if self._fred is None:
            return False
        try:
            df = self._fred.get_series_as_of_date(series_id, self.as_of)
            return df is not None and len(df) > 0
        except Exception:
            return False
