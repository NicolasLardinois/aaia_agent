from unittest.mock import MagicMock

import pandas as pd

import adapters.data.finnhub as fh
from adapters.data.finnhub import FinnhubProvider
from core.utils.scoring import standardized_unexpected_earnings


def _earnings_df(rows: list[tuple[float, float]]) -> pd.DataFrame:
    """rows: (EPS Estimate, Reported EPS) je Quartal, älteste-zuerst."""
    return pd.DataFrame(
        {
            "EPS Estimate": [r[0] for r in rows],
            "Reported EPS": [r[1] for r in rows],
        }
    )


def _provider_with(df: pd.DataFrame, monkeypatch) -> FinnhubProvider:
    fake_ticker = MagicMock()
    fake_ticker.earnings_history = df
    monkeypatch.setattr(fh.yf, "Ticker", lambda _t: fake_ticker)
    return FinnhubProvider("dummy-key")


def test_earnings_history_liefert_actual_und_estimate(monkeypatch):
    """Der Adapter muss pro Quartal `actual` (Reported EPS) und `estimate` (EPS Estimate)
    befüllen — sonst kann die SUE-Logik die Magnitude nicht rechnen (gibt None)."""
    rows = [(1.00, 1.20), (1.10, 1.00), (1.20, 1.50), (1.30, 1.40)]
    provider = _provider_with(_earnings_df(rows), monkeypatch)

    out = provider.get_earnings_history("AAPL")

    assert len(out) == 4
    for q, (estimate, reported) in zip(out, rows):
        assert q["estimate"] == estimate
        assert q["actual"] == reported
        # beat bleibt konsistent zu actual/estimate
        assert q["beat"] is bool(reported > estimate)


def test_earnings_history_speist_sue_produktiv(monkeypatch):
    """Mit actual/estimate kann SUE jetzt produktiv rechnen (vorher immer None)."""
    rows = [(1.00, 1.05), (1.10, 1.08), (1.20, 1.40), (1.30, 1.90)]  # >=4 Quartale, Std>0
    provider = _provider_with(_earnings_df(rows), monkeypatch)

    out = provider.get_earnings_history("AAPL")
    sue = standardized_unexpected_earnings(out)

    assert sue is not None
    # jüngste Surprise (1.90-1.30=0.60) ist die größte → SUE deutlich positiv
    assert sue > 0


def test_earnings_history_ueberspringt_unvollstaendige_zeilen(monkeypatch):
    """Zeilen ohne Estimate ODER Reported EPS werden übersprungen (kein Crash, kein None-Eintrag)."""
    df = _earnings_df([(1.0, 1.1), (1.2, 1.3)])
    df.loc[1, "Reported EPS"] = None  # zweite Zeile unvollständig
    provider = _provider_with(df, monkeypatch)

    out = provider.get_earnings_history("AAPL")

    assert len(out) == 1
    assert out[0]["actual"] == 1.1
    assert out[0]["estimate"] == 1.0
