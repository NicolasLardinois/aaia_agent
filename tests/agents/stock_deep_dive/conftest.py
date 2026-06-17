from unittest.mock import MagicMock

import pandas as pd
import pytest


def make_close_series(values: list[float], start: str = "2021-01-04", freq: str = "B") -> pd.Series:
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float, name="Close")


def make_hist(values: list[float], **kw) -> pd.DataFrame:
    return pd.DataFrame({"Close": make_close_series(values, **kw)})


@pytest.fixture
def bus() -> MagicMock:
    return MagicMock()
