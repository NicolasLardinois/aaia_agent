from datetime import date

import pytest

from core.ports.snapshot_store import SnapshotStore


def test_snapshot_store_ist_abstrakt():
    with pytest.raises(TypeError):
        SnapshotStore()  # abstrakte Methoden nicht implementiert


def test_minimal_subclass_erfuellt_den_vertrag():
    class Dummy(SnapshotStore):
        def __init__(self):
            self.store: dict[tuple[str, str], tuple[date, object]] = {}

        def put(self, namespace, key, obs_date, value):
            self.store[(namespace, key)] = (obs_date, value)

        def get(self, namespace, key, as_of):
            hit = self.store.get((namespace, key))
            if hit and hit[0] <= as_of:
                return hit
            return None

    d = Dummy()
    d.put("ecb", "cpi", date(2026, 6, 1), 2.5)
    assert d.get("ecb", "cpi", date(2026, 7, 1)) == (date(2026, 6, 1), 2.5)
    assert d.get("ecb", "cpi", date(2026, 5, 1)) is None
