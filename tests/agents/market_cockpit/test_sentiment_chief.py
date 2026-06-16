from agents.market_cockpit.sentiment_chief_agent import _aggregate
from core.domain.models import Signal, SignalStatus


def test_two_bullish_one_unavailable_is_bullish():
    items = [
        (Signal.BULLISH, 0.45, SignalStatus.AVAILABLE),   # vix
        (Signal.NEUTRAL, 0.25, SignalStatus.UNAVAILABLE), # fear_greed stub
        (Signal.BULLISH, 0.30, SignalStatus.AVAILABLE),   # put_call
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BULLISH


def test_all_unavailable_is_neutral():
    items = [
        (Signal.NEUTRAL, 0.45, SignalStatus.UNAVAILABLE),
        (Signal.NEUTRAL, 0.25, SignalStatus.UNAVAILABLE),
        (Signal.NEUTRAL, 0.30, SignalStatus.UNAVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.NEUTRAL
