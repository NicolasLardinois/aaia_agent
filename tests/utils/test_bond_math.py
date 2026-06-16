import math
from core.utils.bond_math import bond_price, ytm


def test_par_bond_ytm_equals_coupon():
    assert math.isclose(ytm(100.0, 100.0, 0.05, 10, freq=2), 0.05, abs_tol=1e-4)


def test_discount_bond_ytm_above_coupon():
    y = ytm(95.50, 100.0, 0.05, 10, freq=2)
    assert math.isclose(y, 0.0560, abs_tol=2e-3), y


def test_zero_coupon_ytm():
    y = ytm(67.30, 100.0, 0.0, 10, freq=1)
    assert math.isclose(y, 0.0405, abs_tol=2e-3), y


def test_bond_price_roundtrip():
    # ytm und bond_price müssen inverse zueinander sein
    p = bond_price(0.06, 100.0, 0.05, 10, freq=2)
    assert math.isclose(ytm(p, 100.0, 0.05, 10, freq=2), 0.06, abs_tol=1e-5)
