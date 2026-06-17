import asyncio
from unittest.mock import MagicMock

import pandas as pd

from agents.stock_deep_dive.commodity.seasonality_agent import (
    SeasonalityAgent, _signal, _significant,
)
from core.domain.models import Signal, SignalStatus


def test_significant_positive_bias_is_bullish():
    # klar positiver, signifikanter Monatsbias
    returns = [3.0, 3.2, 2.8, 3.1, 2.9, 3.0, 3.3, 2.7, 3.0, 3.1, 2.8, 3.2, 3.0, 2.9, 3.1, 3.0]
    assert _signal(returns) == Signal.BULLISH


def test_insignificant_bias_is_neutral():
    # hohe Streuung, Median nahe 0 → nicht signifikant → NEUTRAL
    returns = [10.0, -9.0, 8.0, -11.0, 9.0, -8.0, 7.0, -10.0, 6.0, -7.0, 5.0, -6.0, 4.0, -5.0, 3.0, -4.0]
    assert _signal(returns) == Signal.NEUTRAL


def test_too_few_observations_is_neutral():
    assert _signal([3.0, 3.1, 2.9]) == Signal.NEUTRAL


def test_significance_helper():
    assert _significant([3.0] * 16) is True
    assert _significant([0.1, -0.1] * 8) is False


def test_run_unavailable_when_history_short():
    provider = MagicMock()
    provider.get_price_history.return_value = pd.DataFrame(
        {"Close": pd.Series([100.0, 101.0, 102.0])}
    )
    agent = SeasonalityAgent(provider, MagicMock())
    result = asyncio.run(agent.run("ZW=F"))
    assert result.status == SignalStatus.UNAVAILABLE
