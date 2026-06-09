import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from adapters.data.fred_api import FredDataProvider


def _make_provider(series_map: dict):
    """Build a FredDataProvider with a mocked self.fred.get_series."""
    provider = FredDataProvider.__new__(FredDataProvider)
    mock_fred = MagicMock()

    def _get_series(fred_id, **kwargs):
        if fred_id in series_map:
            val = series_map[fred_id]
            if isinstance(val, Exception):
                raise val
            return pd.Series([val])
        raise Exception(f"Unexpected series: {fred_id}")

    mock_fred.get_series.side_effect = _get_series
    provider.fred = mock_fred
    return provider


# Test 1: normale Rückgabe — beide Werte vorhanden
def test_get_yield_spreads_returns_both_values():
    provider = _make_provider({"T10Y2Y": -0.3, "T10Y3M": 0.7})
    result = provider.get_yield_spreads()
    assert result == {"10y2y": -0.3, "10y3m": 0.7}


# Test 2: T10Y2Y schlägt fehl → None für 10y2y, 10y3m noch vorhanden
def test_get_yield_spreads_partial_failure():
    provider = _make_provider({"T10Y2Y": Exception("API error"), "T10Y3M": 0.7})
    result = provider.get_yield_spreads()
    assert result["10y2y"] is None
    assert result["10y3m"] == 0.7


# Test 3: beide schlagen fehl → beide None
def test_get_yield_spreads_full_failure():
    provider = _make_provider({"T10Y2Y": Exception("fail"), "T10Y3M": Exception("fail")})
    result = provider.get_yield_spreads()
    assert result == {"10y2y": None, "10y3m": None}
