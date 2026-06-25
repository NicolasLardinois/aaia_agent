"""Phase 3: reine Futures-Short-Mathematik (Roll-Yield-Short, Floor-Distanz, Carry-State)."""
from core.utils.futures_short import roll_yield_short_ann, floor_distance_pct, carry_state


def test_roll_yield_short_is_plus_slope():
    # Contango (slope>0) ⇒ Short profitiert ⇒ positiver Roll-Yield
    assert roll_yield_short_ann(0.06) == 0.06
    assert roll_yield_short_ann(-0.04) == -0.04
    assert roll_yield_short_ann(0.0) == 0.0


def test_floor_distance_basic():
    assert floor_distance_pct(140.0, 100.0) == 0.40      # 40 % über Kosten
    assert floor_distance_pct(100.0, 100.0) == 0.0       # genau am Boden
    assert floor_distance_pct(90.0, 100.0) == -0.10      # unter den Kosten


def test_floor_distance_no_floor():
    assert floor_distance_pct(100.0, None) is None
    assert floor_distance_pct(100.0, 0.0) is None        # 0/negativ = kein gültiger Boden


def test_carry_state_bands():
    assert carry_state(0.05) == "contango_tailwind"      # genau auf der Bandgrenze
    assert carry_state(0.051) == "contango_tailwind"
    assert carry_state(-0.05) == "backwardation_headwind"
    assert carry_state(0.04) == "neutral"
    assert carry_state(0.0) == "neutral"
    assert carry_state(None) == "neutral"
