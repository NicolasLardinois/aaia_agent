from datetime import datetime
from core.domain.events import MacroChiefReady
from adapters.api.event_serializer import event_to_dict


def test_event_to_dict_maps_all_fields():
    ts = datetime(2026, 6, 22, 10, 15, 3)
    event = MacroChiefReady(source="macro_chief", payload={"regime": "Aufschwung"}, timestamp=ts)
    d = event_to_dict(event, run_id="abc123")
    assert d["type"] == "MacroChiefReady"
    assert d["source"] == "macro_chief"
    assert d["payload"] == {"regime": "Aufschwung"}
    assert d["timestamp"] == "2026-06-22T10:15:03"
    assert d["run_id"] == "abc123"
