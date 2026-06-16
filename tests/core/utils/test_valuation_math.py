import math
import pytest

from core.utils.valuation_math import capm_wacc


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
