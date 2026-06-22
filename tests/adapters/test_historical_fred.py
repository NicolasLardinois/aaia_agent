from datetime import date
import pandas as pd
from adapters.data.historical_fred import HistoricalFredProvider


def _fake_loader(series_map):
    """Baut einen _series_loader, der pro series_id eine feste Reihe liefert,
    bereits auf <= as_of geschnitten (simuliert den Point-in-Time-Schnitt)."""
    def _loader(fred, series_id, as_of):
        idx, vals = series_map[series_id]
        s = pd.Series(vals, index=pd.to_datetime(idx))
        return s[s.index <= pd.Timestamp(as_of)]
    return _loader


def test_get_economic_state_nutzt_nur_werte_bis_as_of():
    # CPI: 13 monatliche Punkte (Jan 2019 bis Jan 2020) für pct_change(12).
    # Der hohe Sprung (130.0) liegt im Jan 2021 = nach dem Stichtag 2020-06-01 → unsichtbar.
    # pct_change(12): Jan 2020 (102.0) vs Jan 2019 (100.0) = +2.0 %.
    cpi_dates = pd.date_range("2019-01-01", periods=13, freq="MS").strftime("%Y-%m-%d").tolist()
    # 100.0 in Jan 2019, linear auf 102.0 in Jan 2020 (13 Punkte = 0..12)
    cpi_vals = [100.0 + i * (2.0 / 12) for i in range(13)]
    # Zukünftiger Wert (nach as_of 2020-06-01): wird vom fake_loader herausgefiltert
    cpi_dates_future = cpi_dates + ["2021-01-01"]
    cpi_vals_future = cpi_vals + [130.0]

    series = {
        "CPIAUCSL": (cpi_dates_future, cpi_vals_future),
        "UNRATE":   (["2019-12-01", "2020-12-01"], [3.5, 6.7]),
        "FEDFUNDS": (["2020-01-01"], [1.5]),
        "T10Y2Y":   (["2020-01-01"], [0.3]),
        "GDP":      (["2018-01-01", "2019-01-01", "2020-01-01"], [100.0, 102.0, 104.0]),
        "UMCSENT":  (["2020-01-01"], [99.0]),
        "INDPRO":   (["2019-01-01", "2020-01-01"], [100.0, 101.0]),
    }
    prov = HistoricalFredProvider("KEY", date(2020, 6, 1), _series_loader=_fake_loader(series))
    state = prov.get_economic_state()
    # unemployment = letzter Wert <= as_of = 3.5 (der 6.7-Wert von 12/2020 ist Zukunft)
    assert state["unemployment"] == 3.5
    # inflation = YoY Jan 2020 vs Jan 2019 = (102-100)/100 = 2.0 % (der 130-Wert ist Zukunft)
    assert round(state["inflation"], 1) == 2.0
