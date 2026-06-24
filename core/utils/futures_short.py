"""Reine Futures-Short-Mathematik (Phase 3).

Keine I/O, keine Provider — nur Float/Modell-in/-out. Begründungen siehe
docs/superpowers/specs/2026-06-24-phase3-futures-short-design.md §3/§6.
Einheiten: slope/Roll-Yield als Dezimal p. a. (0.05 = 5 %); floor_distance als Dezimal."""

from core.domain.models import FuturesCurveSnapshot, FuturesShortAssessment, ShortAction
from core.utils.futures_curve import slope_ann


def roll_yield_short_ann(slope: float) -> float:
    """Roll-Yield für den Short = +slope (Contango = positiver Roll = Rückenwind).

    Spiegelbild zu roll_yield_long_ann = −slope: der Short rollt die Kurve runter und
    profitiert, wenn der Folgekontrakt teurer ist (Contango)."""
    return slope


def floor_distance_pct(spot: float, floor: float | None) -> float | None:
    """Fallhöhe nach unten = (spot − floor)/floor. None, wenn kein gültiger Boden (≤0/None)."""
    if not floor or floor <= 0:
        return None
    return (spot - floor) / floor


def carry_state(slope: float | None) -> str:
    """±5 %-Bänder (identisch zu curve_signal). Contango ⇒ Rückenwind Short, Backwardation ⇒ Gegenwind."""
    if slope is None:
        return "neutral"
    if slope >= 0.05:
        return "contango_tailwind"
    if slope <= -0.05:
        return "backwardation_headwind"
    return "neutral"


def assess_futures_short(snap: FuturesCurveSnapshot | None,
                         cost_floor: float | None) -> FuturesShortAssessment:
    """Kombiniert Carry (Roll-Yield-Short) + Bewertung (Fallhöhe zum Kostenboden) zur
    Short-Konfidenz. Cost-Curve-Boden als Deckel: nahe/unter Boden ODER ohne Boden-Daten
    wird die Konfidenz unter die 0.50-Schwelle gedrückt (Spec §6). Defensiv: snap None → unavailable."""
    if snap is None:
        return FuturesShortAssessment.unavailable()
    slope = slope_ann(snap.front, snap.next_, snap.days_between_expiries)
    ry_short = roll_yield_short_ann(slope) if slope is not None else None
    cstate = carry_state(slope)
    dist = floor_distance_pct(snap.spot, cost_floor)
    floor_applied = dist is not None

    # Bewertungs-Basis: viel Fallhöhe über den Kosten ⇒ mehr Short-Potenzial.
    if dist is None:
        base, floor_binds = 0.10, False
    elif dist >= 0.50:
        base, floor_binds = 0.55, False
    elif dist >= 0.25:
        base, floor_binds = 0.45, False
    elif dist >= 0.10:
        base, floor_binds = 0.30, False
    else:                       # < 0.10 (inkl. negativ) ⇒ am/unter dem Boden
        base, floor_binds = 0.10, True

    # Carry-Adjustment: Contango zahlt den Short (+), Backwardation kostet ihn (−).
    if cstate == "contango_tailwind":
        carry_adj = 0.10
    elif cstate == "backwardation_headwind":
        carry_adj = -0.12
    else:
        carry_adj = 0.0

    conf = max(0.10, min(1.0, base + carry_adj))
    # Cost-Curve-Boden als Deckel + fehlende Boden-Daten ⇒ unter die Schwelle.
    if floor_binds or not floor_applied:
        conf = min(conf, 0.49)

    if floor_binds:
        engine_action = ShortAction.COVER     # am Boden: raus/meiden
    elif conf >= 0.50:
        engine_action = ShortAction.SHORT
    else:
        engine_action = ShortAction.NONE

    return FuturesShortAssessment(
        roll_yield_short_ann=ry_short,
        carry_state=cstate,
        cost_floor=cost_floor,
        floor_distance_pct=dist,
        floor_binds=floor_binds,
        floor_applied=floor_applied,
        short_confidence=round(conf, 2),
        engine_action=engine_action,
        available=True,
    )
