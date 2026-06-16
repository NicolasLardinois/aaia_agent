import math
import pytest
from core.utils.bond_math import bond_price, ytm, _cashflows
from core.utils.bond_math import (
    macaulay_duration, modified_duration, convexity,
    effective_duration, dv01, price_change_estimate,
)
from core.utils.bond_math import yield_to_worst


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


def test_macaulay_par_bond():
    d = macaulay_duration(100.0, 100.0, 0.05, 10, freq=2)
    assert math.isclose(d, 7.99, abs_tol=0.1), d


def test_modified_from_macaulay_consistency():
    mac = macaulay_duration(100.0, 100.0, 0.05, 10, freq=2)
    mod = modified_duration(mac, 0.05, 2)
    assert math.isclose(mod, mac / (1 + 0.05/2), abs_tol=1e-9)
    assert math.isclose(mod, 7.79, abs_tol=0.1), mod


def test_convexity_positive_and_plausible():
    c = convexity(100.0, 100.0, 0.05, 10, freq=2)
    assert 60.0 < c < 95.0, c


def test_effective_duration_matches_modified_for_optionfree():
    # numerisch via paralleler ±25bp-Verschiebung
    y, dy = 0.05, 0.0025
    p0 = 100.0
    pu = bond_price(y + dy, 100.0, 0.05, 10, freq=2)
    pd = bond_price(y - dy, 100.0, 0.05, 10, freq=2)
    eff = effective_duration(pu, pd, p0, dy)
    mod = modified_duration(macaulay_duration(p0, 100.0, 0.05, 10, freq=2), y, 2)
    assert math.isclose(eff, mod, abs_tol=0.1), (eff, mod)


def test_dv01_uses_dirty_price():
    mod = 7.79
    assert math.isclose(dv01(mod, 100.0), 7.79 * 100.0 * 0.0001, abs_tol=1e-9)


def test_price_change_estimate_includes_convexity():
    # ΔP/P = -mod*dy + 0.5*conv*dy^2
    est = price_change_estimate(7.79, 76.0, 0.01)
    assert math.isclose(est, -7.79*0.01 + 0.5*76.0*0.01**2, abs_tol=1e-12)
    assert est > -7.79*0.01  # Convexity hebt die lineare Schätzung an


def test_ytw_picks_lower_of_ytm_and_ytc():
    assert yield_to_worst(0.052, 0.041) == 0.041


def test_ytw_ignores_none_ytc():
    assert yield_to_worst(0.052, None) == 0.052


def test_ytw_both_none_returns_none():
    assert yield_to_worst(None, None) is None


# --- Fix I-1: freq <= 0 Guard ---

def test_cashflows_raises_on_freq_zero():
    with pytest.raises(ValueError, match="freq must be positive"):
        _cashflows(100.0, 0.05, 10, freq=0)


def test_cashflows_raises_on_negative_freq():
    with pytest.raises(ValueError, match="freq must be positive"):
        _cashflows(100.0, 0.05, 10, freq=-1)


def test_ytm_raises_on_freq_zero():
    with pytest.raises(ValueError):
        ytm(100.0, 100.0, 0.05, 10, freq=0)
