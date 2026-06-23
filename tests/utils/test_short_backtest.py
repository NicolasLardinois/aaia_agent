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


from core.utils.short_backtest import grade_entry, grade_exit


def test_grade_entry_correct_when_stock_fell():
    # Aktie fiel 10 % (adj=-0.10); Short-Ertrag = +0.10 - Kosten - Borrow > 0
    correct, payoff = grade_entry(-0.10, borrow=0.0, cost_per_side=0.0)
    assert correct is True
    assert payoff == 0.10


def test_grade_entry_borrow_can_flip_to_wrong():
    # Aktie fiel nur 0,5 % (adj=-0.005), aber Borrow 1 % frisst den Gewinn
    correct, payoff = grade_entry(-0.005, borrow=0.01, cost_per_side=0.0)
    assert correct is False
    assert payoff < 0


def test_grade_entry_break_even_is_not_correct():
    # Short-Ertrag exakt 0 → nicht korrekt (strikt > 0)
    correct, payoff = grade_entry(0.0, borrow=0.0, cost_per_side=0.0)
    assert correct is False
    assert payoff == 0.0


def test_grade_exit_correct_when_stock_rose_after_cover():
    # Nach dem Cover stieg die Aktie 8 % → Ausstieg vermied Verlust → korrekt
    correct, payoff = grade_exit(0.08)
    assert correct is True
    assert payoff == 0.08


def test_grade_exit_wrong_when_stock_kept_falling():
    correct, payoff = grade_exit(-0.04)
    assert correct is False
    assert payoff == -0.04
