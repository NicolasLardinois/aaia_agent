from agents.market_cockpit.yield_curve_chief_agent import _aggregate
from core.domain.models import Signal, SignalStatus


def test_us_bearish_plus_eu_stress_is_bearish():
    items = [
        (Signal.BEARISH, 0.60, SignalStatus.AVAILABLE),   # us curve
        (Signal.BEARISH, 0.40, SignalStatus.AVAILABLE),   # eu sovereign
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH


def test_missing_us_curve_uses_eu_only():
    items = [
        (Signal.NEUTRAL, 0.60, SignalStatus.UNAVAILABLE),
        (Signal.BEARISH, 0.40, SignalStatus.AVAILABLE),
    ]
    sig, _ = _aggregate(items)
    assert sig == Signal.BEARISH
