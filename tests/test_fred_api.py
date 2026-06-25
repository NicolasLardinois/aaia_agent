import math
from unittest.mock import MagicMock, patch

import pandas as pd

from adapters.data.fred_api import FredDataProvider


def _make_provider():
    provider = FredDataProvider.__new__(FredDataProvider)
    provider.fred = MagicMock()
    return provider


def _series(*values, freq="MS"):
    return pd.Series(
        list(values),
        index=pd.date_range("2023-01-01", periods=len(values), freq=freq),
    )


# ── Bug #15: get_economic_state kein try/except ───────────────────────────────

def test_get_economic_state_survives_single_series_failure():
    """Ein FRED-Ausfall für eine Serie darf nicht die ganze Methode crashen."""
    provider = _make_provider()

    def side_effect(series_id, **kwargs):
        if series_id == "CPIAUCSL":
            raise Exception("API timeout")
        return _series(*([1.0] * 15))

    provider.fred.get_series.side_effect = side_effect
    result = provider.get_economic_state()

    assert result.get("inflation") is None          # failed → None
    assert result.get("unemployment") is not None   # andere laufen weiter


def test_get_economic_state_all_failures_returns_all_none():
    provider = _make_provider()
    provider.fred.get_series.side_effect = Exception("FRED down")
    result = provider.get_economic_state()
    assert all(v is None for v in result.values())


# ── Bug #16: iloc[-1] auf NaN-Series nach pct_change(12) ─────────────────────

def test_get_economic_state_nan_from_short_series_returns_none():
    """Weniger als 13 Punkte → pct_change(12).iloc[-1] = NaN → muss None werden."""
    provider = _make_provider()
    short = _series(*([1.0] * 5))  # nur 5 Punkte
    provider.fred.get_series.return_value = short
    result = provider.get_economic_state()
    assert result.get("inflation") is None


def test_get_economic_state_nan_value_becomes_none():
    """Wenn transform einen NaN-Float liefert, muss None zurückgegeben werden."""
    provider = _make_provider()
    import numpy as np
    nan_series = pd.Series([float("nan")] * 3,
                           index=pd.date_range("2023-01-01", periods=3, freq="MS"))
    provider.fred.get_series.return_value = nan_series
    result = provider.get_economic_state()
    assert result.get("unemployment") is None


# ── Bug #33: get_extended_state ruft get_economic_state redundant auf ─────────

def test_get_extended_state_does_not_call_get_economic_state():
    """get_extended_state darf get_economic_state nicht aufrufen (7 extra API-Calls)."""
    provider = _make_provider()

    with patch.object(provider, "get_economic_state") as mock_eco:
        mock_eco.side_effect = AssertionError("should not be called")
        normal = _series(*([2.0] * 20))
        provider.fred.get_series.return_value = normal
        result = provider.get_extended_state()

    assert isinstance(result, dict)


def test_get_extended_state_includes_core_cpi_pce_balance_sheet():
    """USA-Reste: Core-CPI (CPILFESL), PCE (PCEPI), Fed-Bilanz (WALCL) als YoY %."""
    provider = _make_provider()

    def side_effect(series_id, **kwargs):
        if series_id == "CPILFESL":      # Core-CPI: YoY ~3%
            return pd.Series([100.0] * 12 + [103.0] * 12,
                             index=pd.date_range("2022-01-01", periods=24, freq="MS"))
        if series_id == "PCEPI":         # PCE: YoY ~4%
            return pd.Series([100.0] * 12 + [104.0] * 12,
                             index=pd.date_range("2022-01-01", periods=24, freq="MS"))
        if series_id == "WALCL":         # Fed-Bilanz wöchentlich, YoY (52W) ~ -5% (QT)
            return pd.Series([200.0] * 52 + [190.0],
                             index=pd.date_range("2024-01-07", periods=53, freq="W"))
        return pd.Series([1.0] * 24,
                         index=pd.date_range("2022-01-01", periods=24, freq="MS"))

    provider.fred.get_series.side_effect = side_effect
    result = provider.get_extended_state()

    assert result["core_cpi"] == 3.0
    assert result["pce"] == 4.0
    assert result["balance_sheet_growth"] == -5.0


def test_get_extended_state_still_computes_real_wage_growth():
    """Auch ohne get_economic_state()-Call muss real_wage_growth berechnet werden."""
    provider = _make_provider()

    def side_effect(series_id, **kwargs):
        # AHETPI: Nominallohnwachstum → YoY ~4%
        base = pd.Series(
            [100.0] * 12 + [104.0] * 12,
            index=pd.date_range("2022-01-01", periods=24, freq="MS"),
        )
        # CPIAUCSL: Inflation → YoY ~2%
        cpi = pd.Series(
            [200.0] * 12 + [204.0] * 12,
            index=pd.date_range("2022-01-01", periods=24, freq="MS"),
        )
        if series_id == "AHETPI":
            return base
        if series_id == "CPIAUCSL":
            return cpi
        return pd.Series([1.0] * 24,
                         index=pd.date_range("2022-01-01", periods=24, freq="MS"))

    provider.fred.get_series.side_effect = side_effect
    result = provider.get_extended_state()

    assert result.get("real_wage_growth") is not None
    # Nominallohn ~4%, Inflation ~2% → Reallohn ~2%
    assert abs(result["real_wage_growth"] - 2.0) < 0.5
