from datetime import datetime, timezone

import numpy as np
from scipy import stats
from fredapi import Fred

from core.ports.data_provider import MacroDataProvider

# Kern-Makrodaten (Regime-Erkennung)
SERIES = {
    "inflation":             ("CPIAUCSL", lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    "unemployment":          ("UNRATE",   lambda s: s.dropna().iloc[-1]),
    "fed_rate":              ("FEDFUNDS", lambda s: s.dropna().iloc[-1]),
    "yield_curve":           ("T10Y2Y",   lambda s: s.dropna().iloc[-1]),
    "gdp_growth":            ("GDP",      lambda s: s.pct_change(4).dropna().iloc[-1] * 100),
    "consumer_sentiment":    ("UMCSENT",  lambda s: s.dropna().iloc[-1]),
    "industrial_production": ("INDPRO",   lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
}

# Neue Serien: Löhne, Reallöhne, Umlaufgeschwindigkeit, Kredit, Realzins
EXTENDED_SERIES = {
    # Löhne (USA)
    "nominal_wage_growth": ("AHETPI",   lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # Umlaufgeschwindigkeit M2
    "money_velocity":      ("M2V",      lambda s: s.dropna().iloc[-1]),
    # Kreditwachstum: Total Loans & Leases, All Commercial Banks
    "credit_growth":       ("TOTLL",    lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # Realzins 10J (TIPS-basiert)
    "real_rate_10y":       ("DFII10",   lambda s: s.dropna().iloc[-1]),
    # Yield Curve 3M/10J
    "yield_curve_3m10y":   ("T10Y3M",   lambda s: s.dropna().iloc[-1]),
    # M2 Geldmenge (YoY %)
    "m2_growth":           ("M2SL",     lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # PPI (Producer Price Index)
    "ppi":                 ("PPIACO",   lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # Core-CPI (ohne Lebensmittel & Energie) — strukturelle Inflation
    "core_cpi":            ("CPILFESL", lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # PCE-Preisindex (YoY) — das Fed-Inflationsziel von 2% bezieht sich auf PCE, nicht CPI
    "pce":                 ("PCEPI",    lambda s: s.pct_change(12).dropna().iloc[-1] * 100),
    # Fed-Bilanzwachstum (WALCL, wöchentlich → YoY über 52 Wochen); QT = negativ
    "balance_sheet_growth": ("WALCL",   lambda s: s.pct_change(52).dropna().iloc[-1] * 100),
}


class FredDataProvider(MacroDataProvider):
    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def get_economic_state(self) -> dict[str, float]:
        state = {}
        for key, (fred_id, transform) in SERIES.items():
            try:
                data = self.fred.get_series(fred_id, observation_start="2018-01-01")
                value = float(transform(data))
                state[key] = round(value, 3) if not np.isnan(value) else None
            except Exception:
                state[key] = None
        return state

    def get_extended_state(self) -> dict[str, float]:
        """Löhne, Kredit, Geldmenge, Realzins, PPI."""
        state = {}
        for key, (fred_id, transform) in EXTENDED_SERIES.items():
            try:
                data = self.fred.get_series(fred_id, observation_start="2015-01-01")
                value = float(transform(data))
                state[key] = round(value, 3) if not np.isnan(value) else None
            except Exception:
                state[key] = None
        # Reallohnwachstum = Nominallohn - Inflation (inline, kein get_economic_state()-Call)
        nom = state.get("nominal_wage_growth")
        try:
            cpi = self.fred.get_series("CPIAUCSL", observation_start="2015-01-01")
            inf_val = float(cpi.pct_change(12).dropna().iloc[-1] * 100)
            inf = round(inf_val, 3) if not np.isnan(inf_val) else None
        except Exception:
            inf = None
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
            start = f"{datetime.now(timezone.utc).year - years}-01-01"
            wilshire = self.fred.get_series("WILL5000INDFC", observation_start=start).resample("Q").last().dropna()
            gdp      = self.fred.get_series("GDP",           observation_start=start).resample("Q").last().dropna()
            aligned  = wilshire.align(gdp, join="inner")
            ratios   = (aligned[0] / aligned[1] * 100).dropna()
            return [round(float(r), 1) for r in ratios]
        except Exception:
            return []

    def get_real_rate_history(self, years: int = 5) -> list[dict]:
        """DFII10 (10J US-TIPS-Realzins) der letzten `years` Jahre.
        Rueckgabe: [{"date": "YYYY-MM-DD", "real_rate_10y": float}, ...] (aeltester zuerst).
        Bei Fehler/leerer Serie: []."""
        try:
            start = f"{datetime.now(timezone.utc).year - years}-01-01"
            series = self.fred.get_series("DFII10", observation_start=start).dropna()
            return [
                {"date": ts.strftime("%Y-%m-%d"), "real_rate_10y": round(float(v), 3)}
                for ts, v in series.items()
            ]
        except Exception:
            return []

    def get_policy_rate_history(self, years: int = 2) -> list[dict]:
        """FEDFUNDS der letzten `years` Jahre.
        Rueckgabe: [{"date":"YYYY-MM-DD","rate":float}, ...] (aeltester zuerst). Fehler/leer → []."""
        try:
            start = f"{datetime.now(timezone.utc).year - years}-01-01"
            series = self.fred.get_series("FEDFUNDS", observation_start=start).dropna()
            return [
                {"date": ts.strftime("%Y-%m-%d"), "rate": round(float(v), 3)}
                for ts, v in series.items()
            ]
        except Exception:
            return []

    def get_yield_spreads(self) -> dict:
        """10Y-2Y und 10Y-3M Treasury Spreads für den USA-Markt."""
        result = {"10y2y": None, "10y3m": None}
        try:
            s = self.fred.get_series("T10Y2Y", observation_start="2018-01-01")
            result["10y2y"] = round(float(s.dropna().iloc[-1]), 3)
        except Exception:
            pass
        try:
            s = self.fred.get_series("T10Y3M", observation_start="2018-01-01")
            result["10y3m"] = round(float(s.dropna().iloc[-1]), 3)
        except Exception:
            pass
        return result

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
