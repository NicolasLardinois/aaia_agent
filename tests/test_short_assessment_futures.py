"""Phase 3: derive_short_assessment-Zweig für Rohstoff/Edelmetall-Future-Shorts."""
from types import SimpleNamespace

from core.domain.models import FuturesShortAssessment, ShortAction, PositionState
from core.domain.short_assessment import derive_short_assessment
from core.domain.taxonomy import Underlying, Wrapper


def _bottom_up(fs, underlying=Underlying.COMMODITY, wrapper=Wrapper.FUTURE):
    return SimpleNamespace(underlying=underlying, wrapper=wrapper,
                           short_interest=None, futures_short=fs)


def _fs(conf, floor_binds=False, action=ShortAction.SHORT, available=True):
    return FuturesShortAssessment(
        roll_yield_short_ann=0.06, carry_state="contango_tailwind", cost_floor=100.0,
        floor_distance_pct=0.40, floor_binds=floor_binds, floor_applied=True,
        short_confidence=conf, engine_action=action, available=available)


def _derive(bu, current_position):
    return derive_short_assessment(bu, cockpit=None, current_position=current_position,
                                   top_down_available=True, bu_anomaly=None, td_anomaly=None)


def test_strong_curve_no_position_yields_short():
    a = _derive(_bottom_up(_fs(0.55)), PositionState.NONE)
    assert a.short_action == ShortAction.SHORT
    assert a.confidence == 0.55
    assert "carry_short" in a.archetypes


def test_floor_binds_no_position_yields_none():
    a = _derive(_bottom_up(_fs(0.20, floor_binds=True, action=ShortAction.COVER)), PositionState.NONE)
    assert a.short_action == ShortAction.NONE


def test_floor_binds_existing_short_yields_cover():
    a = _derive(_bottom_up(_fs(0.20, floor_binds=True, action=ShortAction.COVER)), PositionState.SHORT)
    assert a.short_action == ShortAction.COVER


def test_unavailable_futures_short_falls_back():
    a = _derive(_bottom_up(_fs(0.55, available=False)), PositionState.SHORT)
    assert a.short_action == ShortAction.HOLD          # bisheriger Fallback (kein Crash)
    assert a.confidence == 0.10


def test_long_position_defers_to_none():
    a = _derive(_bottom_up(_fs(0.55)), PositionState.LONG)
    assert a.short_action == ShortAction.NONE          # Long-Titel → kein Short
