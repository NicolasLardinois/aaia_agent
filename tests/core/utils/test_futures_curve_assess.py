import pytest

from core.domain.models import FuturesCurveSnapshot, FuturesAssessment, Signal
from core.utils.futures_curve import assess_futures_curve


def _snap(**kw):
    base = dict(spot=100.0, front=100.0, next_=106.0, days_to_front_expiry=30,
                days_between_expiries=182, risk_free_rate=0.05, storage_cost=0.0,
                margin_quote=0.10)
    base.update(kw)
    return FuturesCurveSnapshot(**base)


def test_assess_none_is_unavailable():
    a = assess_futures_curve(None)
    assert a.available is False
    assert a.signal == Signal.NEUTRAL


def test_assess_contango_bearish_with_negative_roll():
    a = assess_futures_curve(_snap(front=100.0, next_=106.0))   # +6% → >5% p.a. Contango
    assert a.available is True
    assert a.signal == Signal.BEARISH
    assert a.slope_ann > 0
    assert a.roll_yield_long_ann < 0
    assert a.leverage == pytest.approx(10.0)


def test_assess_backwardation_bullish():
    a = assess_futures_curve(_snap(front=100.0, next_=92.0, spot=101.0))
    assert a.signal == Signal.BULLISH
    assert a.basis == pytest.approx(1.0)
    assert a.roll_yield_long_ann > 0


def test_assess_missing_margin_leaves_leverage_none():
    a = assess_futures_curve(_snap(margin_quote=None))
    assert a.leverage is None
    assert a.signal in (Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL)
