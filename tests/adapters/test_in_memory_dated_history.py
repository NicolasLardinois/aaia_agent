from datetime import date

from adapters.persistence.in_memory_dated_history import InMemoryDatedHistory
from core.ports.dated_history import DatedHistoryPort


def test_implementiert_port():
    assert issubclass(InMemoryDatedHistory, DatedHistoryPort)


def test_seed_via_konstruktor():
    h = InMemoryDatedHistory({"fed_rate": [(date(2026, 1, 1), 4.0), (date(2026, 6, 1), 4.5)]})
    assert h.values("fed_rate") == [
        (date(2026, 1, 1), 4.0),
        (date(2026, 6, 1), 4.5),
    ]


def test_append_idempotent_pro_tag():
    h = InMemoryDatedHistory()
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 1, 1), 4.75)  # gleicher Tag → ueberschreibt
    assert h.values("fed_rate") == [(date(2026, 1, 1), 4.75)]


def test_value_on_or_before_und_latest():
    h = InMemoryDatedHistory({"fed_rate": [(date(2026, 1, 1), 4.5), (date(2026, 3, 1), 5.25)]})
    assert h.value_on_or_before("fed_rate", date(2026, 2, 15)) == 4.5
    assert h.value_on_or_before("fed_rate", date(2025, 12, 31)) is None
    assert h.latest("fed_rate") == (date(2026, 3, 1), 5.25)


def test_unbekannte_serie_ist_leer():
    h = InMemoryDatedHistory()
    assert h.values("nicht_da") == []
    assert h.latest("nicht_da") is None
    assert h.value_on_or_before("nicht_da", date(2026, 1, 1)) is None
