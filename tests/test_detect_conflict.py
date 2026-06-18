from core.domain.models import (
    ShortAssessment, ShortAction, PositionState, Signal,
)
from core.domain.recommendation import detect_conflict


def _sa(conf, archetypes):
    return ShortAssessment(asset_class="equity", short_action=ShortAction.NONE, confidence=conf,
                           archetypes=archetypes, thesis_flags=[], regime_effect="neutral",
                           squeeze_risk="low", hard_to_borrow=False)


def test_long_held_strong_short_is_conflict():
    c, msg = detect_conflict(PositionState.LONG, "mixed", Signal.NEUTRAL, _sa(0.7, ["distress"]), 0.6)
    assert c is True and msg


def test_long_held_weak_short_no_conflict():
    c, _ = detect_conflict(PositionState.LONG, "mixed", Signal.NEUTRAL, _sa(0.3, []), 0.6)
    assert c is False


def test_short_held_bullish_long_is_conflict():
    c, msg = detect_conflict(PositionState.SHORT, "aligned_bullish", Signal.BULLISH, _sa(0.2, []), 0.7)
    assert c is True and msg


def test_flat_no_conflict():
    c, _ = detect_conflict(PositionState.NONE, "aligned_bullish", Signal.BULLISH, _sa(0.8, ["distress"]), 0.8)
    assert c is False
