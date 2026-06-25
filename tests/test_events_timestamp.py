"""TDD: Event-Default-Zeitstempel ist timezone-aware (UTC).

§5/WS-Vertrag (Logbuch): `event_to_dict` serialisiert `event.timestamp.isoformat()`.
War der Default `datetime.utcnow()` (naiv), kam ein ISO-String **ohne** Zeitzone
heraus (z. B. `2026-06-22T10:15:03`) — ein Frontend interpretiert das oft als
*lokale* Zeit. Mit tz-bewusstem Default trägt der String automatisch `+00:00`.
"""
from datetime import timezone

from core.domain.events import AgentEvent, MacroChiefReady


def test_default_timestamp_ist_timezone_aware():
    ev = AgentEvent(source="x", payload={})
    assert ev.timestamp.tzinfo is not None
    assert ev.timestamp.utcoffset() == timezone.utc.utcoffset(None)


def test_default_timestamp_isoformat_traegt_offset():
    """Der serialisierte Zeitstempel trägt jetzt eine Zeitzonen-Kennung (Z/+00:00)."""
    ev = MacroChiefReady(source="macro_chief", payload={})
    iso = ev.timestamp.isoformat()
    assert iso.endswith("+00:00") or iso.endswith("Z")
