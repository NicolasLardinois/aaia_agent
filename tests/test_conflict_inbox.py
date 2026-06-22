from core.domain.models import ConflictItem
from core.domain.conflict_inbox import record_conflict


class _FakeStore:
    def __init__(self, open_item=None, resolved=None):
        self._open, self._resolved, self.saved = open_item, resolved, []

    def find_open(self, t, d):
        return self._open

    def find_latest_resolved(self, t, d):
        return self._resolved

    def save(self, item):
        self.saved.append(item)

    def load_open(self):
        return []

    def resolve(self, cid, dec):
        pass


def test_skip_when_open_exists():
    """Offener Konflikt vorhanden → kein neuer Eintrag (Dedupe)."""
    s = _FakeStore(open_item=ConflictItem("AAPL", "long", "EXIT", "x"))
    assert record_conflict(s, "AAPL", "long", "EXIT", "x", "on_demand") is None
    assert s.saved == []


def test_new_when_none():
    """Kein Konflikt vorhanden → neuen offenen Eintrag anlegen."""
    s = _FakeStore()
    item = record_conflict(s, "AAPL", "long", "HOLD", "x", "on_demand")
    assert item is not None and len(s.saved) == 1 and s.saved[0].status == "open"


def test_reopen_only_on_more_severe():
    """Erledigter HOLD-Konflikt + neues EXIT-Verdikt (schärfer) → Reopen."""
    s = _FakeStore(resolved=ConflictItem("AAPL", "long", "HOLD", "x", status="resolved"))
    assert record_conflict(s, "AAPL", "long", "EXIT", "y", "proactive") is not None
    assert len(s.saved) == 1


def test_no_reopen_when_same_or_milder():
    """Erledigter EXIT-Konflikt + neues HOLD-Verdikt (milder) → kein Reopen."""
    s = _FakeStore(resolved=ConflictItem("AAPL", "long", "EXIT", "x", status="resolved"))
    assert record_conflict(s, "AAPL", "long", "HOLD", "y", "proactive") is None
    assert s.saved == []
