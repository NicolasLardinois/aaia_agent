from unittest.mock import MagicMock

import pandas as pd

from adapters.data.fred_api import FredDataProvider


def _make_provider():
    p = FredDataProvider.__new__(FredDataProvider)
    p.fred = MagicMock()
    return p


def test_maps_series_to_dicts_drops_nan_chronological():
    p = _make_provider()
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    p.fred.get_series.return_value = pd.Series([1.0, float("nan"), 1.2], index=idx)
    out = p.get_real_rate_history(5)
    assert out == [
        {"date": "2024-01-01", "real_rate_10y": 1.0},
        {"date": "2024-01-03", "real_rate_10y": 1.2},
    ]


def test_uses_dfii10_series():
    p = _make_provider()
    p.fred.get_series.return_value = pd.Series(
        [0.5], index=pd.date_range("2024-01-01", periods=1, freq="D")
    )
    p.get_real_rate_history(5)
    assert p.fred.get_series.call_args.args[0] == "DFII10"


def test_returns_empty_on_failure():
    p = _make_provider()
    p.fred.get_series.side_effect = Exception("API down")
    assert p.get_real_rate_history(5) == []
