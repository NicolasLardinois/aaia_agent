from unittest.mock import MagicMock

import pandas as pd

from adapters.data.fred_api import FredDataProvider


def _make_provider():
    p = FredDataProvider.__new__(FredDataProvider)
    p.fred = MagicMock()
    return p


def test_policy_rate_history_maps_and_drops_nan():
    p = _make_provider()
    idx = pd.date_range("2024-01-01", periods=3, freq="MS")
    p.fred.get_series.return_value = pd.Series([4.5, float("nan"), 4.75], index=idx)
    out = p.get_policy_rate_history(2)
    assert out == [
        {"date": "2024-01-01", "rate": 4.5},
        {"date": "2024-03-01", "rate": 4.75},
    ]


def test_policy_rate_history_uses_fedfunds():
    p = _make_provider()
    p.fred.get_series.return_value = pd.Series(
        [4.5], index=pd.date_range("2024-01-01", periods=1, freq="MS")
    )
    p.get_policy_rate_history(2)
    assert p.fred.get_series.call_args.args[0] == "FEDFUNDS"


def test_policy_rate_history_empty_on_failure():
    p = _make_provider()
    p.fred.get_series.side_effect = Exception("API down")
    assert p.get_policy_rate_history(2) == []
