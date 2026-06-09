"""Tests for FredSnbProvider: Swiss yield curve spreads via FRED."""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from adapters.data.fred_snb import FredSnbProvider


def _make_series(value: float) -> pd.Series:
    """Helper: returns a single-element Series for mocked FRED data."""
    return pd.Series([value], index=pd.to_datetime(["2026-01-01"]))


class TestGetYieldSpreads:
    def test_returns_10y3m_spread(self):
        """Normal case: 10y=1.5, 3m=0.8 → spread=0.7."""
        with patch("adapters.data.fred_snb.Fred") as MockFred:
            mock_instance = MagicMock()
            MockFred.return_value = mock_instance

            def side_effect(series_id, **kwargs):
                if series_id == "IRLTLT01CHM156N":
                    return _make_series(1.5)
                if series_id == "IR3TIB01CHM156N":
                    return _make_series(0.8)
                raise ValueError(f"Unexpected series: {series_id}")

            mock_instance.get_series.side_effect = side_effect

            provider = FredSnbProvider(api_key="test-key")
            result = provider.get_yield_spreads()

        assert result == {"10y3m": 0.7}

    def test_10y_failure_yields_none_spread(self):
        """If 10y fetch raises, spread must be None."""
        with patch("adapters.data.fred_snb.Fred") as MockFred:
            mock_instance = MagicMock()
            MockFred.return_value = mock_instance

            def side_effect(series_id, **kwargs):
                if series_id == "IRLTLT01CHM156N":
                    raise Exception("API error")
                if series_id == "IR3TIB01CHM156N":
                    return _make_series(0.8)
                raise ValueError(f"Unexpected series: {series_id}")

            mock_instance.get_series.side_effect = side_effect

            provider = FredSnbProvider(api_key="test-key")
            result = provider.get_yield_spreads()

        assert result == {"10y3m": None}

    def test_3m_failure_yields_none_spread(self):
        """If 3m fetch raises, spread must be None."""
        with patch("adapters.data.fred_snb.Fred") as MockFred:
            mock_instance = MagicMock()
            MockFred.return_value = mock_instance

            def side_effect(series_id, **kwargs):
                if series_id == "IRLTLT01CHM156N":
                    return _make_series(1.5)
                if series_id == "IR3TIB01CHM156N":
                    raise Exception("API error")
                raise ValueError(f"Unexpected series: {series_id}")

            mock_instance.get_series.side_effect = side_effect

            provider = FredSnbProvider(api_key="test-key")
            result = provider.get_yield_spreads()

        assert result == {"10y3m": None}
