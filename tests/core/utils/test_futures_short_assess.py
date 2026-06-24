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


def test_band_boundary_dist_exactly_050():
    # dist exactly 0.50 ⇒ base 0.55 + contango 0.10 → 0.65
    a = assess_futures_short(_snap(150.0, 100.0, 106.0), 100.0)
    assert a.short_confidence == 0.65
    assert a.floor_binds is False
    assert a.engine_action == ShortAction.SHORT


def test_band_boundary_dist_exactly_025():
    # dist exactly 0.25 ⇒ base 0.45 + contango 0.10 → 0.55
    a = assess_futures_short(_snap(125.0, 100.0, 106.0), 100.0)
    assert a.short_confidence == 0.55
    assert a.floor_binds is False


def test_band_boundary_dist_exactly_010_does_not_bind():
    # dist exactly 0.10 ⇒ base 0.30 + contango 0.10 → 0.40, does not bind
    a = assess_futures_short(_snap(110.0, 100.0, 106.0), 100.0)
    assert a.short_confidence == 0.40
    assert a.floor_binds is False
    assert a.engine_action == ShortAction.NONE


def test_just_below_010_binds():
    # dist 0.09 (< 0.10) ⇒ floor_binds True, base 0.10 + contango 0.10 = 0.20, capped to ≤0.49
    a = assess_futures_short(_snap(109.0, 100.0, 106.0), 100.0)
    assert a.short_confidence <= 0.49
    assert a.floor_binds is True
    assert a.engine_action == ShortAction.COVER


def test_neutral_carry_no_adjustment():
    # dist 0.50 ⇒ base 0.55 ; neutral carry (slope ≈ 4%/yr) ⇒ no adjustment → 0.55
    a = assess_futures_short(_snap(150.0, 100.0, 102.0), 100.0)
    assert a.carry_state == "neutral"
    assert a.short_confidence == 0.55
    assert a.engine_action == ShortAction.SHORT


def test_none_slope_yields_none_roll_yield():
    # days_between_expiries=0 ⇒ slope None ⇒ roll_yield_short_ann None, carry_state neutral
    snap = FuturesCurveSnapshot(
        spot=150.0, front=100.0, next_=106.0,
        days_to_front_expiry=30, days_between_expiries=0,
        risk_free_rate=0.05, storage_cost=0.0, margin_quote=0.10
    )
    a = assess_futures_short(snap, 100.0)
    assert a.roll_yield_short_ann is None
    assert a.carry_state == "neutral"
    assert a.available is True
