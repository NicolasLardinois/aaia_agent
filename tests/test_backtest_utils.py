import pytest
from core.utils.backtest import (
    forward_return, market_adjusted_return, is_correct,
    hit_rate_ci, benchmark_for_market, HORIZONS_DAYS, MIN_SAMPLE,
)


def test_forward_return_basic():
    assert forward_return(100.0, 110.0) == pytest.approx(0.10, abs=1e-12)


def test_forward_return_delisted_is_total_loss():
    # Forward-Preis None (delistet/insolvent) → Totalverlust −100 %
    assert forward_return(100.0, None) == pytest.approx(-1.0, abs=1e-12)


def test_forward_return_zero_entry_is_none():
    assert forward_return(0.0, 50.0) is None


def test_market_adjusted_subtracts_benchmark():
    # Asset +10 %, Benchmark +4 % → Alpha +6 %
    assert market_adjusted_return(0.10, 0.04) == pytest.approx(0.06, abs=1e-12)


def test_market_adjusted_none_benchmark_passthrough():
    # Kein Benchmark verfügbar → roher Return
    assert market_adjusted_return(0.10, None) == pytest.approx(0.10, abs=1e-12)


def test_is_correct_bullish_positive_alpha():
    assert is_correct("bullish", 0.02) is True
    assert is_correct("bullish", -0.02) is False


def test_is_correct_bearish_negative_alpha():
    assert is_correct("bearish", -0.02) is True
    assert is_correct("bearish", 0.02) is False


def test_is_correct_buy_sell_short_aliases():
    assert is_correct("BUY", 0.01) is True
    assert is_correct("SELL", -0.01) is True
    assert is_correct("SHORT", -0.01) is True
    assert is_correct("HOLD", 0.0) is False  # HOLD ist keine Richtungswette → nie "correct"


def test_is_correct_no_neutral_class():
    # Kleiner positiver Alpha bei bullish = correct, kein "neutral"-Schlupfloch
    assert is_correct("bullish", 0.001) is True
    assert is_correct("bullish", -0.001) is False


def test_hit_rate_ci_wilson_bounds():
    lo, hi = hit_rate_ci(7, 10)
    assert 0.0 <= lo < 0.7 < hi <= 1.0


def test_hit_rate_ci_zero_n():
    assert hit_rate_ci(0, 0) == (0.0, 0.0)


def test_benchmark_for_market():
    assert benchmark_for_market("USA") == "^GSPC"
    assert benchmark_for_market("CH") == "^SSMI"
    assert benchmark_for_market("DE") == "^STOXX"
    assert benchmark_for_market("unknown") == "^GSPC"


def test_horizons_and_min_sample_constants():
    assert HORIZONS_DAYS == (30, 60, 90)
    assert MIN_SAMPLE >= 10
