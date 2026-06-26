"""Tests für den CBOE-Put/Call-Adapter (Sentiment).

Kein echtes Netz (conftest blockt `requests` global): geprüft wird der defensive
Vertrag — ein blockierter/fehlgeschlagener Call liefert `None` (aktueller Wert)
bzw. `[]` (Historie), statt die Sentiment-Analyse abstürzen zu lassen (§2/§3).
"""
from adapters.data.cboe_put_call import CboePutCallProvider
from core.ports.put_call_source import PutCallSource


def test_implements_port():
    assert isinstance(CboePutCallProvider(), PutCallSource)


def test_blocked_network_latest_is_none():
    # requests ist geblockt → alle Tagesversuche scheitern → defensiv None.
    assert CboePutCallProvider().get_latest() is None


def test_blocked_network_history_is_empty():
    # requests ist geblockt → keine Werte sammelbar → leere Liste (kein Crash).
    assert CboePutCallProvider().get_history(n_days=30) == []
