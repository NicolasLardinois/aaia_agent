"""
sensors.py — Erweiterung 4: Prädiktive Sensoren
================================================
Holt aktuelle Wirtschaftsdaten von der FRED API und
extrapoliert Trends um 3 Monate in die Zukunft.

FRED-Serien:
  CPIAUCSL → Inflation (Consumer Price Index)
  UNRATE   → Arbeitslosenquote
  FEDFUNDS → Leitzins (Federal Funds Rate)
  T10Y2Y   → Zinskurve (10J minus 2J Anleihen) — Rezessionsindikator
  GDP      → BIP-Wachstum
  UMCSENT  → Konsumentenstimmung (University of Michigan)
  INDPRO   → Industrieproduktion
"""

import numpy as np
from scipy import stats
from fredapi import Fred

SERIES = {
    "inflation":             ("CPIAUCSL", lambda s: s.pct_change(12).iloc[-1] * 100),
    "unemployment":          ("UNRATE",   lambda s: s.iloc[-1]),
    "fed_rate":              ("FEDFUNDS", lambda s: s.iloc[-1]),
    "yield_curve":           ("T10Y2Y",   lambda s: s.iloc[-1]),
    "gdp_growth":            ("GDP",      lambda s: s.pct_change(4).iloc[-1] * 100),
    "consumer_sentiment":    ("UMCSENT",  lambda s: s.iloc[-1]),
    "industrial_production": ("INDPRO",   lambda s: s.pct_change(12).iloc[-1] * 100),
}


class EconomicSensor:
    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)

    def get_state(self) -> tuple[dict, dict]:
        """Aktuellen Zustand + Rohdaten von FRED holen"""
        state, raw = {}, {}
        for key, (fred_id, transform) in SERIES.items():
            data       = self.fred.get_series(fred_id, observation_start="2018-01-01")
            state[key] = round(float(transform(data)), 3)
            raw[key]   = data
        return state, raw

    def predict_state(self, raw: dict, months_ahead: int = 3) -> dict:
        """
        Lineare Trendextrapolation auf transformierten Werten (%, nicht Rohdaten).
        Berechnet für jeden Indikator, wo er in N Monaten sein wird.
        """
        # Dieselben Transformationen wie in get_state — auf Zeitreihe anwenden
        transform_series = {
            "inflation":             lambda s: s.pct_change(12) * 100,
            "unemployment":          lambda s: s,
            "fed_rate":              lambda s: s,
            "yield_curve":           lambda s: s,
            "gdp_growth":            lambda s: s.pct_change(4) * 100,
            "consumer_sentiment":    lambda s: s,
            "industrial_production": lambda s: s.pct_change(12) * 100,
        }
        predictions = {}
        for key, series in raw.items():
            transform = transform_series.get(key, lambda s: s)
            transformed = transform(series).dropna().tail(12)
            if len(transformed) < 3:
                continue
            values = transformed.values.astype(float)
            x = np.arange(len(values))
            slope, intercept, *_ = stats.linregress(x, values)
            predictions[key] = round(intercept + slope * (len(values) + months_ahead), 3)
        return predictions

    def get_volatility(self, raw: dict) -> dict:
        """Standardabweichung der transformierten letzten 12 Monate."""
        transform_series = {
            "inflation":             lambda s: s.pct_change(12) * 100,
            "unemployment":          lambda s: s,
            "fed_rate":              lambda s: s,
            "yield_curve":           lambda s: s,
            "gdp_growth":            lambda s: s.pct_change(4) * 100,
            "consumer_sentiment":    lambda s: s,
            "industrial_production": lambda s: s.pct_change(12) * 100,
        }
        result = {}
        for key, series in raw.items():
            transform = transform_series.get(key, lambda s: s)
            transformed = transform(series).dropna().tail(12)
            result[key] = round(float(transformed.std()), 3)
        return result
