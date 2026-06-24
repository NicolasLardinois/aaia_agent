"""Phase 3: assess_futures_short — Konfidenz aus Carry × Floor + Cost-Curve-Deckel."""
from core.domain.models import FuturesCurveSnapshot, ShortAction
from core.utils.futures_short import assess_futures_short


def _snap(spot, front, next_):
    # days_between 182 ⇒ slope ≈ (next_/front − 1)·2 ; days_to_front 30 für T_years
    return FuturesCurveSnapshot(spot=spot, front=front, next_=next_,
                                days_to_front_expiry=30, days_between_expiries=182,
                                risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10)


def test_none_snap_is_unavailable():
    a = assess_futures_short(None, 100.0)
    assert a.available is False
    assert a.engine_action == ShortAction.NONE


def test_far_above_floor_plus_contango_is_short():
    # spot 140 vs floor 100 ⇒ dist 0.40 ⇒ Basis 0.45 ; starkes Contango ⇒ +0.10 ⇒ 0.55
    a = assess_futures_short(_snap(140.0, 100.0, 106.0), 100.0)
    assert a.carry_state == "contango_tailwind"
    assert a.floor_applied is True
    assert a.floor_binds is False
    assert a.short_confidence == 0.55
    assert a.engine_action == ShortAction.SHORT
    assert a.roll_yield_short_ann is not None and a.roll_yield_short_ann > 0


def test_near_floor_binds_and_caps_below_threshold():
    # spot 105 vs floor 100 ⇒ dist 0.05 (<0.10) ⇒ floor_binds ⇒ conf ≤ 0.49 ⇒ COVER
    a = assess_futures_short(_snap(105.0, 100.0, 106.0), 100.0)
    assert a.floor_binds is True
    assert a.short_confidence <= 0.49
    assert a.engine_action == ShortAction.COVER


def test_missing_floor_caps_below_threshold():
    # Kein Boden bekannt ⇒ floor_applied False ⇒ conf ≤ 0.49 ⇒ kein frischer Short
    a = assess_futures_short(_snap(140.0, 100.0, 106.0), None)
    assert a.floor_applied is False
    assert a.floor_binds is False
    assert a.short_confidence <= 0.49
    assert a.engine_action == ShortAction.NONE


def test_backwardation_headwind_reduces_confidence():
    # spot 140 vs floor 100 ⇒ Basis 0.45 ; Backwardation (next_<front) ⇒ −0.12 ⇒ 0.33
    a = assess_futures_short(_snap(140.0, 100.0, 94.0), 100.0)
    assert a.carry_state == "backwardation_headwind"
    assert a.short_confidence == 0.33
    assert a.engine_action == ShortAction.NONE
