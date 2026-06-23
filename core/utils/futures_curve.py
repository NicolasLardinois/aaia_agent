"""Reine Termin­kurven-Mathematik (Futures-Mechanik-Schicht, Phase 2a).

Keine I/O, keine Modelle in diesem Abschnitt — nur Float-in/Float-out. Begründungen
siehe docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md §6.3.
Einheiten: r/u/y und Rückgaben als Dezimal p. a. (0.03 = 3 %); Tage = Kalendertage.
"""
import math

from core.domain.models import Signal


def slope_ann(front: float, next_: float, days_between: int) -> float | None:
    """Annualisierte Kurvenneigung (next_/front − 1)·(365/Δtage). Contango ⇒ > 0."""
    if not front or days_between <= 0:
        return None
    return (next_ / front - 1.0) * (365.0 / days_between)


def roll_yield_long_ann(slope: float) -> float:
    """Roll-Yield für den Long = −slope (Contango = negativer Roll = Gegenwind)."""
    return -slope


def basis(spot: float, front: float) -> float:
    """Basis = Spot − Future. Positiv ⇒ Backwardation."""
    return spot - front


def cost_of_carry_fair(spot: float, r: float, u: float, y: float, T_years: float) -> float:
    """Theoretischer Fair-Future-Preis F = S·e^((r+u−y)·T) (stetige Verzinsung)."""
    return spot * math.exp((r + u - y) * T_years)


def implied_convenience_yield(spot: float, front: float, r: float, u: float, T_years: float) -> float | None:
    """Implizite Convenience-Yield: Cost-of-Carry nach y aufgelöst.

    y = r + u − ln(front/spot)/T. Reine Ableitung aus beobachteten Preisen, **kein**
    Mispricing-Urteil (Design §13.4)."""
    if not spot or T_years <= 0:
        return None
    return r + u - math.log(front / spot) / T_years


def curve_signal(slope: float | None) -> Signal:
    """±5 %-Bänder (Design §6.3a). Lückenlos — jeder Wert fällt in genau eine Klasse.

    Unter ~5 % p. a. liegt die Neigung im Bereich normaler Lager-/Zins-Carry und ist
    nicht richtungsweisend (NEUTRAL); Backwardation ⇒ Knappheit + positiver Roll (BULLISH);
    Contango ⇒ Überangebot + negativer Roll (BEARISH)."""
    if slope is None:
        return Signal.NEUTRAL
    if slope <= -0.05:
        return Signal.BULLISH
    if slope >= 0.05:
        return Signal.BEARISH
    return Signal.NEUTRAL


def roll_warning(days_to_front_expiry: int | None) -> bool:
    """True, wenn der Front-Kontrakt < 5 Handelstage vor Verfall steht (Roll steht an)."""
    if days_to_front_expiry is None:
        return False
    return days_to_front_expiry < 5
