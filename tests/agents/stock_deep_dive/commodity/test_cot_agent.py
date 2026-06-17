import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.commodity.cot_agent import COTAgent, _cot_signal
from core.domain.models import Signal, SignalStatus


def test_index_high_is_contrarian_bearish():
    assert _cot_signal(cot_index=90.0) == Signal.BEARISH


def test_index_low_is_contrarian_bullish():
    assert _cot_signal(cot_index=10.0) == Signal.BULLISH


def test_index_mid_is_neutral():
    assert _cot_signal(cot_index=50.0) == Signal.NEUTRAL


def _hist(nets):
    return [{"date": f"2024-{(i % 12) + 1:02d}-01", "managed_money_net": n, "open_interest": 1000}
            for i, n in enumerate(nets)]


def test_run_computes_index_and_available():
    provider = MagicMock()
    # aktuelle Netto-Long am Maximum → COT-Index ~100 → bearish
    # ≥26 Einträge damit _MIN_HISTORY=26 erfüllt ist
    nets = list(range(10, 10 + 25)) + [200]  # 26 Einträge, letzter ist Maximum
    provider.get_cot_history.return_value = _hist(nets)
    agent = COTAgent(provider, MagicMock())
    result = asyncio.run(agent.run("gold"))
    assert result.status == SignalStatus.AVAILABLE
    assert result.signal == Signal.BEARISH


def test_run_unavailable_when_no_data():
    provider = MagicMock()
    provider.get_cot_history.return_value = []
    agent = COTAgent(provider, MagicMock())
    result = asyncio.run(agent.run("gold"))
    assert result.status == SignalStatus.UNAVAILABLE
    assert result.signal == Signal.NEUTRAL


def test_run_unavailable_when_history_shorter_than_26():
    """Weniger als 26 Wochen-Einträge → Perzentil wertlos → UNAVAILABLE."""
    provider = MagicMock()
    provider.get_cot_history.return_value = _hist([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 200])
    agent = COTAgent(provider, MagicMock())
    result = asyncio.run(agent.run("gold"))
    assert result.status == SignalStatus.UNAVAILABLE
