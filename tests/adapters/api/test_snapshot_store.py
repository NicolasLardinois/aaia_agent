"""Tests fuer JsonCockpitSnapshotStore — persistiert das letzte serialisierte
Cockpit-Snapshot-Dict auf Disk (damit GET /api/cockpit ein Ergebnis auch nach
Server-Neustart liefert). Defensiv wie JsonDatedHistory: fehlende/korrupte Datei
-> None, statt zu crashen."""
from adapters.api.snapshot_store import JsonCockpitSnapshotStore


def test_load_returns_none_when_file_missing(tmp_path):
    store = JsonCockpitSnapshotStore(str(tmp_path / "nope.json"))
    assert store.load() is None


def test_save_then_load_roundtrip(tmp_path):
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    snapshot = {"regime": "Abschwung", "sources_total": 5}
    store.save(snapshot)
    assert store.load() == snapshot


def test_save_creates_parent_directory(tmp_path):
    # Pfad mit noch nicht existierendem Unterordner (analog .cache/) -> wird angelegt
    store = JsonCockpitSnapshotStore(str(tmp_path / "sub" / "dir" / "snap.json"))
    store.save({"x": 1})
    assert store.load() == {"x": 1}


def test_load_returns_none_on_corrupt_file(tmp_path):
    path = tmp_path / "snap.json"
    path.write_text("{ not valid json", encoding="utf-8")
    store = JsonCockpitSnapshotStore(str(path))
    assert store.load() is None


def test_load_returns_none_when_top_level_not_dict(tmp_path):
    # Eine JSON-Liste ist gueltiges JSON, aber kein Snapshot-Dict -> None
    path = tmp_path / "snap.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    store = JsonCockpitSnapshotStore(str(path))
    assert store.load() is None


def test_save_overwrites_previous_snapshot(tmp_path):
    store = JsonCockpitSnapshotStore(str(tmp_path / "snap.json"))
    store.save({"v": 1})
    store.save({"v": 2})
    assert store.load() == {"v": 2}
