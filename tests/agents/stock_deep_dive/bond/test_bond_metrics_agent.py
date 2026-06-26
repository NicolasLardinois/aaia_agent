import asyncio
import logging
import math
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent


def test_run_loggt_warnung_bei_ausgefallener_quelle(caplog):
    # Logging-Pass: ausgefallene Bond-Datenquelle -> sichtbare warning (Default greift weiter).
    prov = MagicMock()
    prov.get_bond_data.side_effect = RuntimeError("FMP down")
    macro = MagicMock()
    macro.get_economic_state.return_value = {}
    agent = BondMetricsAgent(prov, macro, MagicMock())
    with caplog.at_level(logging.WARNING):
        asyncio.run(agent.run("AAA"))
    assert "Bond Metrics Bond-Daten (AAA)" in caplog.text


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


def test_snapshot_traegt_ytw():
    """Plan C: Yield-to-Worst steht jetzt auch im Snapshot, nicht nur im *Ready-Event."""
    agent, bus = _make(
        {"current_price": 95.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},
        {"inflation": 0.02},
    )
    res = asyncio.run(agent.run("X", "corporate"))
    assert res.ytw is not None
    # Ohne Call-Optionen ist YTW = YTM (yield_to_worst(ytm, None)).
    assert math.isclose(res.ytw, res.ytm, abs_tol=1e-9)
    # Snapshot-Wert == Event-Payload-Wert (kein Auseinanderdriften).
    payload = bus.publish.call_args[0][0].payload
    assert payload["ytw"] == res.ytw


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


# --- Fix I-3: YTM auf Dirty-Preis ---

def test_ytm_uses_dirty_price_when_accrued_positive():
    # accrued > 0 → YTM auf Dirty-Preis; höherer Dirty → niedrigere YTM als Clean-basiert
    agent, _ = _make(
        {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0, "accrued_interest": 2.0},
        {"inflation": 0.02},
    )
    res_dirty = asyncio.run(agent.run("X", "government"))
    agent_clean, _ = _make(
        {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},  # kein accrued
        {"inflation": 0.02},
    )
    res_clean = asyncio.run(agent_clean.run("X", "government"))
    assert res_dirty.ytm is not None and res_clean.ytm is not None
    assert res_dirty.ytm < res_clean.ytm, (
        f"Dirty-YTM {res_dirty.ytm} soll < Clean-YTM {res_clean.ytm}"
    )


def test_current_yield_stays_on_clean_price():
    # Current Yield basiert auf Clean-Preis — auch wenn accrued > 0
    agent, _ = _make(
        {"current_price": 95.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0, "accrued_interest": 2.0},
        {"inflation": 0.02},
    )
    res = asyncio.run(agent.run("X", "corporate"))
    expected = 0.05 * 100.0 / 95.0 * 100
    assert math.isclose(res.current_yield, expected, abs_tol=1e-3)


# --- Fix M-3: to_real guard bei inflation == -100 % ---

def test_real_yield_none_when_inflation_minus_100():
    agent, _ = _make(
        {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
         "maturity_years": 10, "face": 100.0},
        {"inflation": -1.0},  # -1.0 Dezimal == -100 % → to_real wirft ValueError
    )
    res = asyncio.run(agent.run("X", "government"))
    assert res.real_yield is None
