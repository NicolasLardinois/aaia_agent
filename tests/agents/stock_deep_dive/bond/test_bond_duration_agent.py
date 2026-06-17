import asyncio
import math
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from core.domain.models import Signal
from core.utils.bond_math import ytm as _ytm


def _make(bond_data):
    prov = MagicMock()
    prov.get_bond_data.return_value = bond_data
    return BondDurationAgent(prov, MagicMock())


_PAR = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
        "maturity_years": 10, "face": 100.0, "accrued_interest": 1.5}


def test_modified_from_macaulay_consistent():
    # YTM wird auf Dirty-Preis gerechnet (clean + accrued); Konsistenzformel mod = mac / (1 + y/freq)
    dirty = _PAR["current_price"] + _PAR["accrued_interest"]
    y = _ytm(dirty, _PAR["face"], _PAR["coupon_rate"], _PAR["maturity_years"], _PAR["frequency"])
    res = asyncio.run(_make(_PAR).run("X"))
    assert math.isclose(res.modified_duration,
                        res.macaulay_duration / (1 + y / _PAR["frequency"]), abs_tol=1e-3)


def test_convexity_is_computed_not_none():
    res = asyncio.run(_make(_PAR).run("X"))
    assert res.convexity is not None and res.convexity > 0


def test_dv01_uses_dirty_price():
    res = asyncio.run(_make(_PAR).run("X"))
    dirty = 100.0 + 1.5
    assert math.isclose(res.dv01, res.modified_duration * dirty * 0.0001, abs_tol=1e-4)


def test_signal_continuous_via_price_change():
    # rising rates + lange Duration → erwartete Kursänderung deutlich negativ → BEARISH
    res = asyncio.run(_make(_PAR).run("X", rate_direction="rising"))
    assert res.signal == Signal.BEARISH
    res2 = asyncio.run(_make(_PAR).run("X", rate_direction="falling"))
    assert res2.signal == Signal.BULLISH


# --- Fix I-1: freq=0 darf den Agent nicht zum Absturz bringen ---

def test_freq_zero_returns_none_fields():
    data = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 0,
            "maturity_years": 10, "face": 100.0}
    res = asyncio.run(_make(data).run("X"))
    assert res.macaulay_duration is None
    assert res.modified_duration is None
    assert res.convexity is None
    assert res.dv01 is None


# --- Fix I-3: YTM auf Dirty-Preis (clean + accrued) ---

def test_ytm_on_dirty_differs_from_clean_when_accrued_positive():
    # accrued > 0 → dirty > clean → YTM sollte leicht niedriger sein als auf Clean-Preis
    data_with_accrued = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
                         "maturity_years": 10, "face": 100.0, "accrued_interest": 2.0}
    data_without_accrued = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
                            "maturity_years": 10, "face": 100.0}
    # Mit Accrued: dirty=102 → YTM < Clean-basiertem YTM (dirty > face für Par-Bond)
    from core.utils.bond_math import ytm as _ytm_fn
    ytm_dirty = _ytm_fn(102.0, 100.0, 0.05, 10, freq=2)
    ytm_clean = _ytm_fn(100.0, 100.0, 0.05, 10, freq=2)
    assert ytm_dirty < ytm_clean, f"Dirty YTM {ytm_dirty} soll < Clean YTM {ytm_clean} sein"


def test_par_bond_no_accrued_ytm_unchanged():
    # accrued=0 → dirty == clean → YTM identisch wie vorher
    data = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
            "maturity_years": 10, "face": 100.0, "accrued_interest": 0.0}
    res = asyncio.run(_make(data).run("X"))
    assert math.isclose(res.modified_duration,
                        res.macaulay_duration / (1 + 0.05/2), abs_tol=1e-3)
