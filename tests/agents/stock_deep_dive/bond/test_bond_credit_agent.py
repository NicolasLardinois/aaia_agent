import asyncio
import math
from unittest.mock import MagicMock
from agents.stock_deep_dive.bond.bond_credit_agent import _category, _default_prob, BondCreditAgent


def test_sp_ccc_not_50pct_regression():
    # früher: "CCC".startswith("C") → 50 %. Jetzt exakter Lookup ~14 %.
    assert _default_prob("CCC") < 0.30


def test_pd_decimal_baa3():
    assert math.isclose(_default_prob("Baa3"), 0.0018, abs_tol=1e-6)


def test_aaa_zero_pd():
    assert _default_prob("Aaa") == 0.0


def test_category_binary_ig():
    assert _category("Baa3") == "investment_grade"
    assert _category("Ba1") == "high_yield"   # Non-IG
    assert _category(None) == "unrated"


def test_no_junk_class_anymore():
    # "junk" entfällt zugunsten der binären IG/Non-IG-Konvention
    assert _category("CCC") == "high_yield"


def test_pd_derived_from_same_primary_as_category():
    prov = MagicMock()
    prov.get_bond_data.return_value = {"rating_sp": "CCC", "rating_moodys": None,
                                       "rating_trend": "stable"}
    res = asyncio.run(BondCreditAgent(prov, MagicMock()).run("X"))
    assert res.default_probability is not None and res.default_probability < 0.30
    assert res.category == "high_yield"
