"""Reine Futures-Short-Mathematik (Phase 3).

Keine I/O, keine Provider — nur Float/Modell-in/-out. Begründungen siehe
docs/superpowers/specs/2026-06-24-phase3-futures-short-design.md §3/§6.
Einheiten: slope/Roll-Yield als Dezimal p. a. (0.05 = 5 %); floor_distance als Dezimal."""


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
