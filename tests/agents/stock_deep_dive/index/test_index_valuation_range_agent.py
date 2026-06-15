from agents.stock_deep_dive.index.index_valuation_range_agent import (
    _method1_score, _method2_score, _combine,
)
from core.domain.models import Signal


# ── Method 1: EPS × KGV-Band ─────────────────────────────────────────────

def test_m1_at_price_low_is_max_bullish():
    assert _method1_score(3300, price_low=3300, price_mid=3960, price_high=5500) == 1.0

def test_m1_at_price_mid_is_neutral():
    assert _method1_score(3960, price_low=3300, price_mid=3960, price_high=5500) == 0.0

def test_m1_at_price_high_is_max_bearish():
    assert _method1_score(5500, price_low=3300, price_mid=3960, price_high=5500) == -1.0

def test_m1_below_price_low_clamped():
    assert _method1_score(2000, price_low=3300, price_mid=3960, price_high=5500) == 1.0

def test_m1_above_price_high_clamped():
    assert _method1_score(7000, price_low=3300, price_mid=3960, price_high=5500) == -1.0

def test_m1_midpoint_bullish_side():
    """Halbweg zwischen price_low und price_mid → +0.5."""
    mid_low = (3300 + 3960) / 2   # 3630
    score = _method1_score(mid_low, price_low=3300, price_mid=3960, price_high=5500)
    assert abs(score - 0.5) < 0.01


# ── Method 2: P/E vs. historischer Durchschnitt ───────────────────────────

def test_m2_at_pe_mid_is_neutral():
    assert _method2_score(18.0, pe_mid=18.0) == 0.0

def test_m2_30pct_below_is_max_bullish():
    assert _method2_score(18.0 * 0.70, pe_mid=18.0) == 1.0

def test_m2_30pct_above_is_max_bearish():
    assert _method2_score(18.0 * 1.30, pe_mid=18.0) == -1.0

def test_m2_15pct_below_is_half_bullish():
    score = _method2_score(18.0 * 0.85, pe_mid=18.0)
    assert abs(score - 0.5) < 0.01

def test_m2_none_is_neutral():
    assert _method2_score(None, pe_mid=18.0) == 0.0


# ── _combine: Fuzzy-Aggregation mit Schwelle 0.7 ─────────────────────────

def test_combine_both_max_bullish():
    _, sig = _combine(1.0, 1.0)
    assert sig == Signal.BULLISH

def test_combine_both_at_threshold():
    _, sig = _combine(0.7, 0.7)
    assert sig == Signal.BULLISH

def test_combine_one_max_one_neutral_is_neutral():
    """Eine Methode neutral → Durchschnitt 0.5 → NEUTRAL."""
    _, sig = _combine(1.0, 0.0)
    assert sig == Signal.NEUTRAL

def test_combine_both_moderately_bullish():
    """Beide moderat bullish → avg 0.75 → BULLISH."""
    _, sig = _combine(0.8, 0.7)
    assert sig == Signal.BULLISH

def test_combine_both_max_bearish():
    _, sig = _combine(-1.0, -1.0)
    assert sig == Signal.BEARISH

def test_combine_methods_disagree_is_neutral():
    _, sig = _combine(1.0, -1.0)
    assert sig == Signal.NEUTRAL
