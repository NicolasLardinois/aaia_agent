from agents.stock_deep_dive.index.index_valuation_range_agent import (
    _method1_score, _erp_score, _combine, _FUZZY_THRESHOLD,
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


# ── Method 2 (ERP): echt unabhängige Zinsbrücke ───────────────────────────

def test_threshold_lowered_to_realistic_value():
    assert _FUZZY_THRESHOLD <= 0.40


def test_erp_score_high_erp_is_bullish():
    # PE 12 -> E/P 0.0833; riskfree 0.02 -> ERP 0.063 -> deutlich positiv -> +Score
    score = _erp_score(pe_trailing=12.0, riskfree=0.02)
    assert score > 0.5


def test_erp_score_negative_erp_is_bearish():
    # PE 25 -> E/P 0.04; riskfree 0.045 -> ERP -0.005 -> negativ
    score = _erp_score(pe_trailing=25.0, riskfree=0.045)
    assert score < 0.0


def test_erp_score_missing_data_is_neutral():
    assert _erp_score(pe_trailing=None, riskfree=0.03) == 0.0
    assert _erp_score(pe_trailing=20.0, riskfree=None) == 0.0


# ── _combine: Fuzzy-Aggregation mit neuer Schwelle 0.30 ──────────────────

def test_combine_both_max_bullish():
    _, sig = _combine(1.0, 1.0)
    assert sig == Signal.BULLISH

def test_combine_both_at_threshold():
    _, sig = _combine(_FUZZY_THRESHOLD, _FUZZY_THRESHOLD)
    assert sig == Signal.BULLISH

def test_combine_both_max_bearish():
    _, sig = _combine(-1.0, -1.0)
    assert sig == Signal.BEARISH

def test_combine_methods_disagree_is_neutral():
    _, sig = _combine(1.0, -1.0)
    assert sig == Signal.NEUTRAL

def test_combine_moderate_signal_now_votes():
    # avg 0.4 löst jetzt (Schwelle 0.30) BULLISH aus — vorher (0.70) NEUTRAL.
    _, sig = _combine(0.5, 0.3)
    assert sig == Signal.BULLISH
