from core.utils.short_backtest import borrow_cost, BORROW_RATE_NORMAL, BORROW_RATE_HTB


def test_borrow_normal_prorated():
    # 1 %/Jahr über 365 Tage = 1 %
    assert borrow_cost(365, hard_to_borrow=False) == BORROW_RATE_NORMAL


def test_borrow_htb_higher():
    assert borrow_cost(365, hard_to_borrow=True) == BORROW_RATE_HTB


def test_borrow_manual_overrides():
    assert borrow_cost(365, hard_to_borrow=True, manual_rate=0.20) == 0.20


def test_borrow_zero_days():
    assert borrow_cost(0, hard_to_borrow=True) == 0.0


def test_borrow_prorated_half_year():
    assert borrow_cost(182, hard_to_borrow=False) == BORROW_RATE_NORMAL * (182 / 365.0)
