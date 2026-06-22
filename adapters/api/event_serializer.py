"""Pure Serialisierung eines AgentEvent fuer den WebSocket-Stream.

run_id wird mitgegeben, damit das Frontend Events einem Lauf zuordnen kann
(v1 hat keinen Lock — ueberlappende Laeufe waeren sonst ununterscheidbar).
"""
from typing import Any

from core.domain.events import AgentEvent


def event_to_dict(event: AgentEvent, run_id: str) -> dict[str, Any]:
    return {
        "type": type(event).__name__,
        "source": event.source,
        "payload": event.payload,
        "timestamp": event.timestamp.isoformat(),
        "run_id": run_id,
    }
