from core.utils.conflict_backtest import VALID_VERDICTS, grade_verdict, held_return


def test_held_return_long_is_raw():
    assert held_return("long", -0.10) == -0.10


def test_held_return_short_is_flipped():
    # Short gewinnt, wenn der Kurs fällt: adj=-0.10 → r=+0.10
    assert held_return("short", -0.10) == 0.10


def test_hold_correct_when_position_gained():
    correct, payoff = grade_verdict("HOLD", 0.08)
    assert correct is True and payoff == 0.08


def test_hold_wrong_at_zero():
    correct, _ = grade_verdict("HOLD", 0.0)   # strikt > 0
    assert correct is False


def test_exit_correct_when_position_would_have_lost():
    correct, payoff = grade_verdict("EXIT", -0.05)
    assert correct is True and payoff == 0.05   # vermiedener Verlust


def test_exit_wrong_at_zero():
    correct, _ = grade_verdict("EXIT", 0.0)     # strikt < 0
    assert correct is False


def test_reverse_needs_to_clear_costs():
    # -r muss nach Round-Trip-Kosten (2*cost_per_side) im Plus sein
    correct, payoff = grade_verdict("REVERSE", -0.10, cost_per_side=0.0005)
    assert correct is True
    assert payoff == 0.10 - 2 * 0.0005          # apply_costs(-r=0.10)


def test_reverse_wrong_when_reversal_too_small_after_costs():
    # -r = 0.0005 < Kosten 0.001 → Gegenposition zahlt nicht → falsch
    correct, payoff = grade_verdict("REVERSE", -0.0005, cost_per_side=0.0005)
    assert correct is False
    assert payoff < 0


def test_valid_verdicts_set():
    assert VALID_VERDICTS == {"HOLD", "EXIT", "REVERSE"}
