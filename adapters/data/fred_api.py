from datetime import datetime

import numpy as np
from scipy import stats
from fredapi import Fred

from core.ports.data_provider import MacroDataProvider

# Kern-Makrodaten (Regime-Erkennung)
SERIES = {
    "inflation":             ("CPIAUCSL", lambda s: s.pct_change(12).iloc[-1] * 100),
    "unemployment":          ("UNRATE",   lambda s: s.iloc[-1]),
    "fed_rate":              ("FEDFUNDS", lambda s: s.iloc[-1]),
    "yield_curve":           ("T10Y2Y",   lambda s: s.iloc[-1]),
    "gdp_growth":            ("GDP",      lambda s: s.pct_change(4).iloc[-1] * 100),
    "consumer_sentiment":    ("UMCSENT",  lambda s: s.iloc[-1]),
    "industrial_production": ("INDPRO",   lambda s: s.pct_change(12).iloc[-1] * 100),
}

# Neue Serien: Löhne, Reallöhne, Umlaufgeschwindigkeit, Kredit, Realzins
EXTENDED_SERIES = {
    # Löhne (USA)
    "nominal_wage_growth": ("AHETPI",   lambda s: s.pct_change(12).iloc[-1] * 100),
    # Umlaufgeschwindigkeit M2
    "money_velocity":      ("M2V",      lambda s: s.iloc[-1]),
    # Kreditwachstum: Total Loans & Leases, All Commercial Banks
    "credit_growth":       ("TOTLL",    lambda s: s.pct_change(12).iloc[-1] * 100),
    # Realzins 10J (TIPS-basiert)
    "real_rate_10y":       ("DFII10",   lambda s: s.iloc[-1]),
    # Yield Curve 3M/10J
    "yield_curve_3m10y":   ("T10Y3M",   lambda s: s.iloc[-1]),
    # M2 Geldmenge (YoY %)
    "m2_growth":           ("M2SL",     lambda s: s.pct_change(12).iloc[-1] * 100),
    # PPI (Producer Price Index)
    "ppi":                 ("PPIACO",   lambda s: s.pct_change(12).iloc[-1] * 100),
}


class FredDataProvider(MacroDataProvider):
    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def get_economic_state(self) -> dict[str, float]:
        state = {}
        for key, (fred_id, transform) in SERIES.items():
            data = self.fred.get_series(fred_id, observation_start="2018-01-01")
            state[key] = round(float(transform(data)), 3)
        return state

    def get_extended_state(self) -> dict[str, float]:
        """Löhne, Kredit, Geldmenge, Realzins, PPI."""
        state = {}
        for key, (fred_id, transform) in EXTENDED_SERIES.items():
            try:
                data = self.fred.get_series(fred_id, observation_start="2015-01-01")
                state[key] = round(float(transform(data)), 3)
            except Exception:
                state[key] = None
        # Reallohnwachstum = Nominallohn - Inflation
        nom = state.get("nominal_wage_growth")
        inf = self.get_economic_state().get("inflation")
        if nom is not None and inf is not None:
            state["real_wage_growth"] = round(nom - inf, 3)
        return state

    def get_buffett_data(self) -> dict[str, float]:
        """Wilshire 5000 Full Cap (WILL5000INDFC) und US-BIP (GDP) von FRED."""
        try:
            market_cap = float(self.fred.get_series("WILL5000INDFC").dropna().iloc[-1])
            gdp        = float(self.fred.get_series("GDP").dropna().iloc[-1])
            return {"market_cap_bn": market_cap, "gdp_bn": gdp}
        except Exception:
            return {"market_cap_bn": None, "gdp_bn": None}

    def get_buffett_history(self, years: int = 10) -> list[float]:
        """Quartalsweise Buffett-Quoten (%) der letzten N Jahre, älteste zuerst."""
        try:
            start = f"{datetime.utcnow().year - years}-01-01"
            wilshire = self.fred.get_series("WILL5000INDFC", observation_start=start).resample("Q").last().dropna()
            gdp      = self.fred.get_series("GDP",           observation_start=start).resample("Q").last().dropna()
            aligned  = wilshire.align(gdp, join="inner")
            ratios   = (aligned[0] / aligned[1] * 100).dropna()
            return [round(float(r), 1) for r in ratios]
        except Exception:
            return []

    def get_raw_series(self) -> dict:
        raw = {}
        for key, (fred_id, _) in SERIES.items():
            raw[key] = self.fred.get_series(fred_id, observation_start="2018-01-01")
        return raw

    def predict_trend(self, months_ahead: int = 3) -> dict[str, float]:
        transform_map = {
            "inflation":             lambda s: s.pct_change(12) * 100,
            "unemployment":          lambda s: s,
            "fed_rate":              lambda s: s,
            "yield_curve":           lambda s: s,
            "gdp_growth":            lambda s: s.pct_change(4) * 100,
            "consumer_sentiment":    lambda s: s,
            "industrial_production": lambda s: s.pct_change(12) * 100,
        }
        raw = self.get_raw_series()
        predictions = {}
        for key, series in raw.items():
            transformed = transform_map[key](series).dropna().tail(12)
            if len(transformed) < 3:
                continue
            values = transformed.values.astype(float)
            x = np.arange(len(values))
            slope, intercept, *_ = stats.linregress(x, values)
            predictions[key] = round(intercept + slope * (len(values) + months_ahead), 3)
        return predictions
