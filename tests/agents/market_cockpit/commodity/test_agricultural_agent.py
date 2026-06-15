from agents.market_cockpit.commodity.agricultural_agent import _signal
from core.domain.models import Signal


def test_all_neutral_returns_neutral():
    assert _signal([0.05, 0.03, -0.02, 0.01, 0.08, -0.05, 0.04]) == Signal.NEUTRAL


def test_majority_above_20pct_is_bearish():
    # Median > 0.20 → BEARISH
    assert _signal([0.25, 0.30, 0.22, 0.28, 0.35, 0.10, 0.21]) == Signal.BEARISH


def test_single_outlier_does_not_trigger_bearish():
    # Nur Orangensaft explodiert — Median bleibt tief
    assert _signal([0.80, 0.03, 0.02, -0.01, 0.05, 0.04, 0.01]) == Signal.NEUTRAL


def test_majority_below_minus_20pct_is_bullish():
    # Median < -0.20 → BULLISH
    assert _signal([-0.25, -0.30, -0.22, -0.28, -0.35, -0.10, -0.21]) == Signal.BULLISH


def test_empty_returns_neutral():
    assert _signal([]) == Signal.NEUTRAL


def test_single_value_above_threshold_is_bearish():
    assert _signal([0.25]) == Signal.BEARISH


def test_single_value_below_threshold_is_bullish():
    assert _signal([-0.25]) == Signal.BULLISH
