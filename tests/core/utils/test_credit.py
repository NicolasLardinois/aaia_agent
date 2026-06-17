import math
from core.utils.credit import (
    normalize_rating, default_probability,
    credit_triangle_spread, is_investment_grade,
)


def test_sp_ccc_not_mapped_to_moodys_c_50pct():
    # Der historische Bug: "CCC".startswith("C") → 0.50. Jetzt: ~0.14 (CCC).
    pd = default_probability("CCC")
    assert pd < 0.30, f"CCC darf nicht ~50% sein, war {pd}"


def test_normalize_sp_and_moodys_to_same_bucket():
    assert normalize_rating("BBB-") == normalize_rating("Baa3")
    assert normalize_rating("AAA") == normalize_rating("Aaa")
    assert normalize_rating("ccc+") == normalize_rating("Caa1")  # case-insensitiv


def test_pd_is_decimal_not_percent():
    # B: historisch 4.3 % → jetzt 0.043 Dezimal
    assert math.isclose(default_probability("B"), 0.043, abs_tol=1e-6)
    assert math.isclose(default_probability("Aaa"), 0.0, abs_tol=1e-9)
    assert math.isclose(default_probability("Baa3"), 0.0018, abs_tol=1e-6)


def test_credit_triangle_spread_pd_times_lgd():
    # PD 0.043, Recovery 0.40 → LGD 0.60 → Spread ≈ 0.0258 (258 bp)
    assert math.isclose(credit_triangle_spread(0.043, 0.60), 0.0258, abs_tol=1e-6)


def test_ig_boundary_binary():
    assert is_investment_grade("BBB-") is True
    assert is_investment_grade("Baa3") is True
    assert is_investment_grade("BB+") is False
    assert is_investment_grade("Ba1") is False
    assert is_investment_grade(None) is False


def test_unknown_rating_returns_none_pd():
    assert default_probability("ZZZ") is None
    assert normalize_rating("ZZZ") is None
