import math
import pytest

from core.utils.valuation_math import capm_wacc
from core.utils.valuation_math import two_stage_dcf
from core.utils.valuation_math import earnings_yield, equity_risk_premium, shiller_cape


def test_capm_wacc_textbook_numbers():
    # Cost of equity = rf + beta*ERP = 0.04 + 1.2*0.05 = 0.10
    # After-tax cost of debt = 0.05*(1-0.21) = 0.0395
    # WACC = 0.6*0.10 + 0.4*0.0395 = 0.06 + 0.0158 = 0.0758
    wacc = capm_wacc(
        rf=0.04, beta=1.2, erp=0.05,
        cost_of_debt=0.05, tax_rate=0.21,
        equity_weight=0.6, debt_weight=0.4,
    )
    assert math.isclose(wacc, 0.0758, abs_tol=1e-6)


def test_capm_wacc_all_equity_financed():
    # equity_weight=1.0 → WACC == cost of equity
    wacc = capm_wacc(
        rf=0.03, beta=1.0, erp=0.055,
        cost_of_debt=0.06, tax_rate=0.25,
        equity_weight=1.0, debt_weight=0.0,
    )
    assert math.isclose(wacc, 0.085, abs_tol=1e-9)


def test_capm_wacc_weights_normalized_when_not_summing_to_one():
    # equity_weight=3, debt_weight=1 → effektiv 0.75 / 0.25
    wacc = capm_wacc(
        rf=0.04, beta=1.0, erp=0.05,
        cost_of_debt=0.05, tax_rate=0.20,
        equity_weight=3.0, debt_weight=1.0,
    )
    # ke=0.09, kd_after=0.04 → 0.75*0.09 + 0.25*0.04 = 0.0675 + 0.01 = 0.0775
    assert math.isclose(wacc, 0.0775, abs_tol=1e-9)


def test_two_stage_dcf_known_value():
    # fcf0=10, growth=0%, terminal_growth=0%, wacc=10%, years=5
    # FCF jedes Jahr = 10 (kein Wachstum)
    # PV(explizit) = 10*(1.1^-1 + ... + 1.1^-5) = 10*3.790786769 = 37.90786769
    # TV am Jahr 5 = FCF_5*(1+0)/(0.10-0) = 10/0.10 = 100; PV(TV)=100*1.1^-5=62.09213231
    # Summe = 100.0
    value = two_stage_dcf(fcf0=10.0, growth=0.0, terminal_growth=0.0, wacc=0.10, years=5)
    assert abs(value - 100.0) < 1e-6


def test_two_stage_dcf_high_growth_increases_value():
    base = two_stage_dcf(fcf0=10.0, growth=0.00, terminal_growth=0.02, wacc=0.10, years=5)
    fast = two_stage_dcf(fcf0=10.0, growth=0.15, terminal_growth=0.02, wacc=0.10, years=5)
    assert fast > base


def test_two_stage_dcf_lower_wacc_increases_value():
    high_wacc = two_stage_dcf(fcf0=10.0, growth=0.05, terminal_growth=0.02, wacc=0.12, years=5)
    low_wacc  = two_stage_dcf(fcf0=10.0, growth=0.05, terminal_growth=0.02, wacc=0.08, years=5)
    assert low_wacc > high_wacc


def test_two_stage_dcf_stable_when_wacc_near_terminal_growth():
    # WACC sehr nah an terminal_growth -> kein Crash, endlicher Wert
    value = two_stage_dcf(fcf0=5.0, growth=0.05, terminal_growth=0.025, wacc=0.026, years=5)
    assert value == value  # not NaN
    assert value > 0
    assert value < 1e9     # nicht explodiert


def test_two_stage_dcf_wacc_below_terminal_growth_does_not_explode():
    # Ökonomisch unzulässig (WACC < g_term) -> Mindestabstand greift, endlich & positiv
    value = two_stage_dcf(fcf0=5.0, growth=0.05, terminal_growth=0.04, wacc=0.03, years=5)
    assert value > 0
    assert value < 1e9


def test_earnings_yield_inverse_of_pe():
    assert earnings_yield(20.0) == 0.05
    assert earnings_yield(25.0) == 0.04


def test_earnings_yield_none_or_nonpositive_returns_none():
    assert earnings_yield(None) is None
    assert earnings_yield(0.0) is None
    assert earnings_yield(-10.0) is None


def test_equity_risk_premium():
    # E/P = 0.05, riskfree 10y = 0.03 -> ERP = 0.02
    assert abs(equity_risk_premium(0.05, 0.03) - 0.02) < 1e-9


def test_equity_risk_premium_none_inputs():
    assert equity_risk_premium(None, 0.03) is None
    assert equity_risk_premium(0.05, None) is None


def test_shiller_cape_basic():
    # price 4000, mean(10J real EPS) = 200 -> CAPE = 20
    assert shiller_cape(4000.0, [180, 190, 200, 210, 220, 200, 200, 200, 200, 200]) == 20.0


def test_shiller_cape_empty_or_nonpositive_mean_returns_none():
    assert shiller_cape(4000.0, []) is None
    assert shiller_cape(4000.0, [0.0, 0.0]) is None
    assert shiller_cape(None, [200.0]) is None
