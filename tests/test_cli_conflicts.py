"""Tests für die CLI-Befehle 'conflicts' und 'resolve' in app/main.py.

Getestet werden die reinen Funktionen run_conflicts(store) und run_resolve(store, id, decision).
Kein echter DB-Zugriff — der Store wird als SimpleNamespace-Stub übergeben.
"""

from types import SimpleNamespace as NS

from app.main import run_conflicts, run_resolve


def test_run_conflicts_lists(capsys):
    """run_conflicts gibt Ticker, Verdict und ID aus."""
    store = NS(load_open=lambda: [
        NS(id=3, ticker="AAPL", direction="long", verdict="EXIT", reason="screent short")
    ])
    run_conflicts(store)
    out = capsys.readouterr().out
    assert "AAPL" in out and "EXIT" in out and "#3" in out


def test_run_conflicts_empty(capsys):
    """run_conflicts meldet 'Keine offenen Konflikte', wenn die Liste leer ist."""
    store = NS(load_open=lambda: [])
    run_conflicts(store)
    out = capsys.readouterr().out
    assert "Keine offenen Konflikte" in out


def test_run_resolve_valid():
    """run_resolve ruft store.resolve(int(id), decision) auf — gültige Entscheidung."""
    calls = []
    store = NS(resolve=lambda i, d: calls.append((i, d)))
    run_resolve(store, "3", "held")
    assert calls == [(3, "held")]


def test_run_resolve_valid_closed():
    """run_resolve akzeptiert auch 'closed' als gültige Entscheidung."""
    calls = []
    store = NS(resolve=lambda i, d: calls.append((i, d)))
    run_resolve(store, "7", "closed")
    assert calls == [(7, "closed")]


def test_run_resolve_invalid_does_not_write():
    """run_resolve schreibt nichts bei ungültiger Entscheidung ('foo' ist nicht erlaubt)."""
    calls = []
    store = NS(resolve=lambda i, d: calls.append((i, d)))
    run_resolve(store, "3", "foo")
    assert calls == []
