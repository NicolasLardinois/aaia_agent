"""Pure Serialisierung eines CockpitResult in den Frontend-Vertrag (Regime-Uebersicht).

Kein I/O. UNAVAILABLE ist ein eigener Zustand (status), nicht NEUTRAL/0 — eine
ausgefallene Domaene zaehlt NICHT in sources_active (AGENTS.md §3 / Frontend §5.4).
Macro wird durch das Regime-Banner repraesentiert (kein eigenes Signal-Feld im
Modell); die vier Sub-Domaenen tragen ihr eigenes overall-signal.
"""
from core.domain.models import CockpitResult, SignalStatus


def cockpit_to_dict(result: CockpitResult) -> dict:
    domains = [
        {"key": "commodities", "signal": result.commodities.signal.value,        "status": result.commodities.status.value},
        {"key": "sentiment",   "signal": result.sentiment.signal.value,          "status": result.sentiment.status.value},
        {"key": "yield_curve", "signal": result.yield_curve.signal.value,        "status": result.yield_curve.status.value},
        {"key": "sectors",     "signal": result.sectors.rotation.signal.value,   "status": result.sectors.status.value},
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
