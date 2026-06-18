from core.domain.models import Recommendation, ShortAction, PositionState


def test_recommendation_has_new_members():
    assert Recommendation.BUY_PLUS.value == "BUY+"
    assert Recommendation.NONE.value == "NONE"
    assert Recommendation.SHORT.value == "SHORT"  # transitional, bleibt


def test_short_action_members():
    assert {a.value for a in ShortAction} == {"SHORT", "SHORT+", "HOLD", "COVER", "NONE"}


def test_position_state_members():
    assert PositionState.NONE.value == "none"
    assert PositionState.LONG.value == "long"
    assert PositionState.SHORT.value == "short"
