import asyncio
import math
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent


def _make(bond_data, state):
    prov = MagicMock()
    prov.get_bond_data.return_value = bond_data
    macro = MagicMock()
    macro.get_economic_state.return_value = state
    bus = MagicMock()
    return BondMetricsAgent(prov, macro, bus), bus


def test_computes_ytm_from_raw_inputs_par_bond():
    agent, _ = _make(
        {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},
        {"inflation": 0.02, "breakeven_inflation": 0.022},
    )
    res = asyncio.run(agent.run("UST10", "government"))
    assert math.isclose(res.ytm, 0.05, abs_tol=1e-3), res.ytm


def test_current_yield_uses_clean_price_convention():
    agent, _ = _make(
        {"current_price": 95.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},
        {"inflation": 0.02},
    )
    res = asyncio.run(agent.run("X", "corporate"))
    # current_yield (in %) = 0.05*100 / 95 * 100
    assert math.isclose(res.current_yield, 0.05*100/95*100, abs_tol=1e-3)


def test_real_yield_uses_breakeven_not_realized():
    agent, _ = _make(
        {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},
        {"inflation": 0.04, "breakeven_inflation": 0.025},
    )
    res = asyncio.run(agent.run("X", "government"))
    # ytw/infl sind Dezimal (0.05/0.025); Plan-0-to_real erwartet Prozentpunkte:
    # to_real(5.0, 2.5) ≈ 2.44 (Prozentpunkte) — NICHT 0.05-0.04
    assert res.real_yield > 2.0, res.real_yield


def test_yield_to_worst_for_callable():
    agent, _ = _make(
        {"current_price": 105.0, "coupon_rate": 0.06, "frequency": 2,
         "maturity_years": 10, "face": 100.0,
         "call_price": 100.0, "years_to_call": 3},
        {"inflation": 0.02},
    )
    res = asyncio.run(agent.run("X", "corporate"))
    assert res.ytc is not None and res.ytc < res.ytm
