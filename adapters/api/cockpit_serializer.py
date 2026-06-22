"""Pure Serialisierung eines CockpitResult in den Frontend-Vertrag (Regime-Uebersicht).

Kein I/O. UNAVAILABLE ist ein eigener Zustand (status), nicht NEUTRAL/0 — eine
ausgefallene Domaene zaehlt NICHT in sources_active (AGENTS.md §3 / Frontend §5.4).
Macro wird durch das Regime-Banner repraesentiert (kein eigenes Signal-Feld im
Modell); die vier Sub-Domaenen tragen ihr eigenes overall-signal.
"""
from typing import Any

from core.domain.models import CockpitResult, Signal, SignalStatus


def _domain(key: str, signal: Signal, status: SignalStatus) -> dict[str, Any]:
    """Eine Domaenen-Kachel fuer den Frontend-Vertrag.

    UNAVAILABLE ≠ NEUTRAL (AGENTS.md §3 / Spec §6): eine ausgefallene Domaene
    traegt im Default Signal.NEUTRAL — das darf NICHT als echtes Signal nach
    aussen, sonst sieht ein Consumer ein erfundenes "neutral" fuer eine Quelle
    ohne Daten. Bei status=unavailable ist signal daher None.
    """
    available = status is SignalStatus.AVAILABLE
    return {
        "key": key,
        "signal": signal.value if available else None,
        "status": status.value,
    }


def cockpit_to_dict(result: CockpitResult) -> dict[str, Any]:
    domains = [
        _domain("commodities", result.commodities.signal,        result.commodities.status),
        _domain("sentiment",   result.sentiment.signal,          result.sentiment.status),
        _domain("yield_curve", result.yield_curve.signal,        result.yield_curve.status),
        _domain("sectors",     result.sectors.rotation.signal,   result.sectors.status),
    ]
    macro_available = result.macro.status is SignalStatus.AVAILABLE
    sources_active = (1 if macro_available else 0) + sum(
        1 for d in domains if d["status"] == SignalStatus.AVAILABLE.value
    )
    return {
        "regime": result.macro.regime.value,
        "regime_confidence": result.macro.regime_confidence,
        "macro_status": result.macro.status.value,
        "domains": domains,
        "sources_active": sources_active,
        "sources_total": 1 + len(domains),  # Macro + 4 Sub-Domaenen
    }
