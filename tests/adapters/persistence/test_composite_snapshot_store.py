from datetime import date

from adapters.persistence.composite_snapshot_store import CompositeSnapshotStore
from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory


def _store(tmp_path):
    return CompositeSnapshotStore(InMemoryDatedHistory(), str(tmp_path / "blobs.json"))


def test_skalar_geht_in_datedhistory_und_kommt_datiert_zurueck(tmp_path):
    s = _store(tmp_path)
    s.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    assert s.get("ecb", "cpi", date(2026, 7, 1)) == (date(2026, 6, 1), 2.5)


def test_get_liefert_frischesten_wert_kleiner_gleich_as_of(tmp_path):
    s = _store(tmp_path)
    s.put("ecb", "cpi", date(2026, 5, 1), 2.0)
    s.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    # as_of zwischen beiden → älterer Wert
    assert s.get("ecb", "cpi", date(2026, 5, 15)) == (date(2026, 5, 1), 2.0)
    # as_of vor allem → None
    assert s.get("ecb", "cpi", date(2026, 4, 1)) is None


def test_payload_geht_in_blob_und_ueberlebt_neue_instanz(tmp_path):
    path = str(tmp_path / "blobs.json")
    s1 = CompositeSnapshotStore(InMemoryDatedHistory(), path)
    s1.put("yahoo.price_history", "AAPL:1y", date(2026, 6, 1), '{"schema": "x"}')
    # Neue Instanz liest die persistierte Blob-Datei.
    s2 = CompositeSnapshotStore(InMemoryDatedHistory(), path)
    assert s2.get("yahoo.price_history", "AAPL:1y", date(2026, 7, 1)) == (
        date(2026, 6, 1), '{"schema": "x"}')


def test_bool_gilt_nicht_als_skalar_sondern_als_payload(tmp_path):
    # bool ist Subklasse von int — darf NICHT in die float-Zeitreihe.
    s = _store(tmp_path)
    s.put("ns", "flag", date(2026, 6, 1), True)
    assert s.get("ns", "flag", date(2026, 7, 1)) == (date(2026, 6, 1), True)


def test_leerer_store_liefert_none(tmp_path):
    s = _store(tmp_path)
    assert s.get("ecb", "cpi", date(2026, 7, 1)) is None
