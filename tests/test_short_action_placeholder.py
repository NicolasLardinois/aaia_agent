from core.domain.models import ShortAction, PositionState
from core.domain.recommendation import derive_short_action_placeholder


def test_short_position_holds():
    assert derive_short_action_placeholder(PositionState.SHORT) == ShortAction.HOLD


def test_long_defers_to_none():
    assert derive_short_action_placeholder(PositionState.LONG) == ShortAction.NONE


def test_flat_is_none():
    assert derive_short_action_placeholder(PositionState.NONE) == ShortAction.NONE
