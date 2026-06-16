import asyncio
import math
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from core.domain.models import Signal


def _make(bond_data):
    prov = MagicMock()
    prov.get_bond_data.return_value = bond_data
    return BondDurationAgent(prov, MagicMock())


_PAR = {"current_price": 100.0, "coupon_rate": 0.05, "frequency": 2,
        "maturity_years": 10, "face": 100.0, "accrued_interest": 1.5}


def test_modified_from_macaulay_consistent():
    res = asyncio.run(_make(_PAR).run("X"))
    assert math.isclose(res.modified_duration,
                        res.macaulay_duration / (1 + 0.05/2), abs_tol=1e-3)


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
