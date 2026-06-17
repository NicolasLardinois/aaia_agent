import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.precious_metals.cross_metal_agent import (
    CrossMetalAgent, _ratio_signal,
)
from core.domain.models import Signal, SignalStatus


def test_high_gs_percentile_is_bullish_for_silver():
    # GS-Ratio im 95. Perzentil → Silber relativ billig → bullish Silber
    assert _ratio_signal(pct=95.0, metal="silver", high_favours="second") == Signal.BULLISH


def test_high_gs_percentile_is_bearish_for_gold():
    # selber Zustand, aber Metall = Gold → bearish Gold
    assert _ratio_signal(pct=95.0, metal="gold", high_favours="second") == Signal.BEARISH


def test_low_gs_percentile_is_bearish_for_silver():
    assert _ratio_signal(pct=5.0, metal="silver", high_favours="second") == Signal.BEARISH


def test_mid_percentile_is_neutral():
    assert _ratio_signal(pct=50.0, metal="silver", high_favours="second") == Signal.NEUTRAL


def test_missing_data_is_unavailable():
    provider = MagicMock()
    provider.get_price_history.return_value = None
    agent = CrossMetalAgent(provider, MagicMock())
    result = asyncio.run(agent.run("gold"))
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL


def test_gold_platinum_signal_is_emitted_for_platinum():
    # hoher Gold/Platin-Quotient (95. Perzentil) → Platin relativ billig → bullish Platin
    import pandas as pd
    provider = MagicMock()

    def hist(ticker, period="2y"):
        # konstruiere Ratio-Historie so, dass aktueller Quotient extrem hoch ist
        if ticker == "GC=F":
            return pd.DataFrame({"Close": pd.Series([2000.0] * 250 + [4000.0])})
        if ticker == "SI=F":
            return pd.DataFrame({"Close": pd.Series([25.0] * 251)})
        if ticker == "PL=F":
            return pd.DataFrame({"Close": pd.Series([1000.0] * 251)})
        return None

    provider.get_price_history.side_effect = hist
    agent = CrossMetalAgent(provider, MagicMock())
    result = asyncio.run(agent.run("platinum"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BULLISH
