from agents.stock_deep_dive.index.index_valuation_range_agent import _combine
from core.domain.models import Signal


def test_both_bullish_is_bullish():
    _, sig = _combine(m1_pts=1, m2_pts=1)
    assert sig == Signal.BULLISH


def test_both_bearish_is_bearish():
    _, sig = _combine(m1_pts=-1, m2_pts=-1)
    assert sig == Signal.BEARISH


def test_only_one_bullish_is_neutral():
    """Einzelne Methode reicht nicht für BULLISH."""
    _, sig = _combine(m1_pts=1, m2_pts=0)
    assert sig == Signal.NEUTRAL


def test_only_one_bearish_is_neutral():
    """Einzelne Methode reicht nicht für BEARISH."""
    _, sig = _combine(m1_pts=-1, m2_pts=0)
    assert sig == Signal.NEUTRAL


def test_methods_disagree_is_neutral():
    _, sig = _combine(m1_pts=1, m2_pts=-1)
    assert sig == Signal.NEUTRAL


def test_both_neutral_is_neutral():
    _, sig = _combine(m1_pts=0, m2_pts=0)
    assert sig == Signal.NEUTRAL
