"""Phase 3: FuturesShortAssessment-Modell + BottomUpResult-Feld."""
from core.domain.models import FuturesShortAssessment, ShortAction


def test_unavailable_is_neutral_and_not_available():
    a = FuturesShortAssessment.unavailable()
    assert a.available is False
    assert a.engine_action == ShortAction.NONE
    assert a.floor_binds is False
    assert a.floor_applied is False
    assert a.short_confidence == 0.10
    assert a.roll_yield_short_ann is None


def test_can_construct_available():
    a = FuturesShortAssessment(
        roll_yield_short_ann=0.06, carry_state="contango_tailwind",
        cost_floor=60.0, floor_distance_pct=0.40, floor_binds=False,
        floor_applied=True, short_confidence=0.55, engine_action=ShortAction.SHORT,
        available=True)
    assert a.available is True
    assert a.carry_state == "contango_tailwind"


def test_bottom_up_result_defaults_futures_short_none():
    from core.domain.models import BottomUpResult
    import dataclasses
    f = {fld.name for fld in dataclasses.fields(BottomUpResult)}
    assert "futures_short" in f
