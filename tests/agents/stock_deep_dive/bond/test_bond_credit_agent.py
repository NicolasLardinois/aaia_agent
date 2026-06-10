from agents.stock_deep_dive.bond.bond_credit_agent import _default_prob, _category


def test_baa3_gets_baa_default_rate_not_ba():
    prob = _default_prob("Baa3")
    assert prob == 0.18, f"Expected 0.18 (Baa), got {prob}"


def test_aaa_gets_zero_default_rate():
    assert _default_prob("Aaa") == 0.0


def test_ba1_gets_ba_default_rate():
    assert _default_prob("Ba1") == 1.2


def test_none_rating_returns_unrated_category():
    assert _category(None) == "unrated"


def test_baa1_is_investment_grade():
    assert _category("Baa1") == "investment_grade"
