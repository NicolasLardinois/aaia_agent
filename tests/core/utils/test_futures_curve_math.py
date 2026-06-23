import math

import pytest

from core.utils.futures_curve import (
    slope_ann, roll_yield_long_ann, basis,
    cost_of_carry_fair, implied_convenience_yield,
)


def test_slope_ann_contango_positive():
    # next_ 5% über front auf 182 Tage → ~+10% p.a.
    s = slope_ann(front=100.0, next_=105.0, days_between=182)
    assert s == pytest.approx(0.05 * 365 / 182, rel=1e-6)
    assert s > 0


def test_slope_ann_backwardation_negative():
    assert slope_ann(front=100.0, next_=95.0, days_between=182) < 0


def test_slope_ann_guards_zero_days_and_zero_front():
    assert slope_ann(front=100.0, next_=105.0, days_between=0) is None
    assert slope_ann(front=0.0, next_=105.0, days_between=182) is None


def test_roll_yield_is_negated_slope():
    assert roll_yield_long_ann(0.08) == -0.08
    assert roll_yield_long_ann(-0.08) == 0.08


def test_basis_sign():
    assert basis(spot=101.0, front=100.0) == pytest.approx(1.0)   # Backwardation
    assert basis(spot=99.0, front=100.0) == pytest.approx(-1.0)   # Contango


def test_cost_of_carry_fair_pure_rate_for_metals():
    # u=y=0 → reiner Zins-Carry F = S·e^(r·T)
    f = cost_of_carry_fair(spot=2000.0, r=0.05, u=0.0, y=0.0, T_years=1.0)
    assert f == pytest.approx(2000.0 * math.exp(0.05))


def test_implied_convenience_yield_inverts_cost_of_carry():
    # Backwardation (front<spot) bei r,u klein → positive Convenience-Yield
    y = implied_convenience_yield(spot=100.0, front=98.0, r=0.05, u=0.0, T_years=0.5)
    expected = 0.05 + 0.0 - math.log(98.0 / 100.0) / 0.5
    assert y == pytest.approx(expected)
    assert y > 0


def test_implied_convenience_yield_guards():
    assert implied_convenience_yield(spot=0.0, front=98.0, r=0.05, u=0.0, T_years=0.5) is None
    assert implied_convenience_yield(spot=100.0, front=98.0, r=0.05, u=0.0, T_years=0.0) is None
