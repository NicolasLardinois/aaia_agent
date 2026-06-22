"""Tests für SupabaseConflictStore — gemockter DB-Cursor, kein echter Connect.

Mock-Muster identisch zu test_supabase_memory.py:
  - SupabaseConflictStore.__new__ umgeht __init__ (kein SUPABASE_DB_URL nötig).
  - _connect wird über monkeypatch ersetzt.
  - cur = MagicMock(); conn.cursor.side_effect = fake_cursor.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from adapters.persistence.supabase_conflict_store import SupabaseConflictStore
from core.domain.models import ConflictItem


# ── Hilfs-Fixtures ─────────────────────────────────────────────────────────────

def _make_item(**kwargs) -> ConflictItem:
    """Minimaler ConflictItem-Stub für die Tests."""
    defaults = dict(
        ticker="AAPL",
        direction="long",
        verdict="EXIT",
        reason="Analyse widerspricht Position",
        status="open",
        source="on_demand",
    )
    defaults.update(kwargs)
    return ConflictItem(**defaults)


def _patch_store(monkeypatch, cur):
    """Gibt einen SupabaseConflictStore zurück, dessen _connect gemockt ist."""
    @contextmanager
    def fake_cursor():
        yield cur

    conn = MagicMock()
    conn.cursor.side_effect = fake_cursor

    @contextmanager
    def fake_connect(self):
        yield conn

    monkeypatch.setattr(SupabaseConflictStore, "_connect", fake_connect)
    # __new__ umgeht __init__ — kein SUPABASE_DB_URL nötig (gleiche Technik wie supabase_memory)
    store = SupabaseConflictStore.__new__(SupabaseConflictStore)
    return store, conn


# ── save ───────────────────────────────────────────────────────────────────────

def test_save_fuehrt_insert_aus(monkeypatch):
    """save(item) muss INSERT INTO conflicts ausführen, ticker/direction/verdict/status enthalten."""
    cur = MagicMock()
    store, conn = _patch_store(monkeypatch, cur)
    item = _make_item()

    store.save(item)

    assert cur.execute.called, "cur.execute wurde nicht aufgerufen"
    sql, params = cur.execute.call_args.args
    assert "INSERT INTO CONFLICTS" in sql.upper()
    assert "ticker" in sql
    assert "direction" in sql
    assert "verdict" in sql
    assert "status" in sql
    # Werte müssen in den Parametern stecken
    assert "AAPL" in params
    assert "long" in params
    assert "EXIT" in params
    assert "open" in params
    conn.commit.assert_called_once()


def test_save_db_fehler_kein_crash(monkeypatch):
    """DB-Fehler beim save → no-op, kein Exception nach oben."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("DB down")
    store, _conn = _patch_store(monkeypatch, cur)
    # Darf nicht werfen
    store.save(_make_item())


# ── resolve ────────────────────────────────────────────────────────────────────

def test_resolve_fuehrt_update_aus(monkeypatch):
    """resolve(7, 'held') muss UPDATE conflicts SET status='resolved' … WHERE id=%s ausführen."""
    cur = MagicMock()
    store, conn = _patch_store(monkeypatch, cur)

    store.resolve(7, "held")

    assert cur.execute.called
    sql, params = cur.execute.call_args.args
    assert "UPDATE" in sql.upper()
    assert "conflicts" in sql.lower()
    assert "status" in sql
    assert "resolved" in sql
    assert "user_decision" in sql
    # Parameter-Reihenfolge: (user_decision, id) — user_decision zuerst, id am Ende (WHERE-Bedingung)
    assert "held" in params
    assert 7 in params
    conn.commit.assert_called_once()


def test_resolve_db_fehler_kein_crash(monkeypatch):
    """DB-Fehler beim resolve → no-op, kein Exception nach oben."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("DB down")
    store, _conn = _patch_store(monkeypatch, cur)
    store.resolve(99, "closed")


# ── load_open ──────────────────────────────────────────────────────────────────

def _fake_rows() -> list[dict]:
    """Zwei gemockte DB-Zeilen mit status='open'."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": 1, "ticker": "AAPL", "direction": "long",
            "verdict": "EXIT", "reason": "r1", "status": "open",
            "source": "on_demand", "user_decision": None,
            "created_at": now, "resolved_at": None,
        },
        {
            "id": 2, "ticker": "TSLA", "direction": "short",
            "verdict": "REVERSE", "reason": "r2", "status": "open",
            "source": "proactive", "user_decision": None,
            "created_at": now, "resolved_at": None,
        },
    ]


def test_load_open_mappt_zeilen_zu_conflict_items(monkeypatch):
    """load_open() muss zwei gemockte Zeilen in zwei ConflictItem mit status='open' mappen."""
    cur = MagicMock()
    cur.fetchall.return_value = _fake_rows()
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.load_open()

    assert len(result) == 2
    assert all(isinstance(i, ConflictItem) for i in result)
    assert all(i.status == "open" for i in result)
    assert result[0].ticker == "AAPL"
    assert result[1].ticker == "TSLA"
    assert result[0].id == 1
    assert result[1].id == 2


def test_load_open_query_filtert_nach_status(monkeypatch):
    """load_open() muss WHERE status='open' in der Query haben."""
    cur = MagicMock()
    cur.fetchall.return_value = []
    store, _conn = _patch_store(monkeypatch, cur)

    store.load_open()

    sql = cur.execute.call_args.args[0]
    assert "status" in sql
    assert "open" in sql


def test_load_open_db_fehler_gibt_leere_liste(monkeypatch):
    """DB-Fehler beim load_open → [] zurück, kein Crash."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("DB down")
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.load_open()

    assert result == []


# ── find_open ──────────────────────────────────────────────────────────────────

def test_find_open_gibt_conflict_item_zurueck(monkeypatch):
    """find_open(ticker, direction) → ConflictItem wenn Zeile vorhanden."""
    now = datetime.now(timezone.utc)
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": 3, "ticker": "AAPL", "direction": "long",
        "verdict": "EXIT", "reason": "r", "status": "open",
        "source": "on_demand", "user_decision": None,
        "created_at": now, "resolved_at": None,
    }
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.find_open("AAPL", "long")

    assert isinstance(result, ConflictItem)
    assert result.ticker == "AAPL"
    assert result.status == "open"


def test_find_open_gibt_none_wenn_keine_zeile(monkeypatch):
    """find_open → None wenn fetchone() None zurückgibt."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.find_open("AAPL", "long")

    assert result is None


def test_find_open_query_filtert_nach_status_open(monkeypatch):
    """find_open muss status='open' in der Query haben."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    store, _conn = _patch_store(monkeypatch, cur)

    store.find_open("AAPL", "long")

    sql, params = cur.execute.call_args.args
    assert "open" in sql
    assert "AAPL" in params
    assert "long" in params


def test_find_open_db_fehler_gibt_none(monkeypatch):
    """DB-Fehler bei find_open → None, kein Crash."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("DB down")
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.find_open("AAPL", "long")

    assert result is None


# ── find_latest_resolved ───────────────────────────────────────────────────────

def test_find_latest_resolved_gibt_conflict_item_zurueck(monkeypatch):
    """find_latest_resolved(ticker, direction) → ConflictItem wenn Zeile vorhanden."""
    now = datetime.now(timezone.utc)
    cur = MagicMock()
    cur.fetchone.return_value = {
        "id": 5, "ticker": "MSFT", "direction": "long",
        "verdict": "HOLD", "reason": "r", "status": "resolved",
        "source": "on_demand", "user_decision": "held",
        "created_at": now, "resolved_at": now,
    }
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.find_latest_resolved("MSFT", "long")

    assert isinstance(result, ConflictItem)
    assert result.status == "resolved"
    assert result.user_decision == "held"


def test_find_latest_resolved_query_filtert_nach_status_resolved(monkeypatch):
    """find_latest_resolved muss status='resolved' in der Query haben."""
    cur = MagicMock()
    cur.fetchone.return_value = None
    store, _conn = _patch_store(monkeypatch, cur)

    store.find_latest_resolved("MSFT", "long")

    sql, params = cur.execute.call_args.args
    assert "resolved" in sql
    assert "MSFT" in params
    assert "long" in params


def test_find_latest_resolved_db_fehler_gibt_none(monkeypatch):
    """DB-Fehler bei find_latest_resolved → None, kein Crash."""
    cur = MagicMock()
    cur.execute.side_effect = Exception("DB down")
    store, _conn = _patch_store(monkeypatch, cur)

    result = store.find_latest_resolved("MSFT", "long")

    assert result is None


# ── Connect-Fehler (noch vor dem Cursor) ──────────────────────────────────────

def test_connect_fehler_bei_save_kein_crash(monkeypatch):
    """Wenn _connect selbst wirft → save no-op, kein Crash."""
    @contextmanager
    def broken_connect(self):
        raise Exception("Connect failed")
        yield  # noqa: unreachable — macht contextmanager happy

    monkeypatch.setattr(SupabaseConflictStore, "_connect", broken_connect)
    store = SupabaseConflictStore.__new__(SupabaseConflictStore)
    store.save(_make_item())  # darf nicht werfen


def test_connect_fehler_bei_load_open_gibt_leere_liste(monkeypatch):
    """Wenn _connect selbst wirft → load_open gibt [], kein Crash."""
    @contextmanager
    def broken_connect(self):
        raise Exception("Connect failed")
        yield

    monkeypatch.setattr(SupabaseConflictStore, "_connect", broken_connect)
    store = SupabaseConflictStore.__new__(SupabaseConflictStore)
    result = store.load_open()
    assert result == []
