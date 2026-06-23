"""TDD Task 7 – Quality-Fix: _resolve_taxonomy() in app/main.py.

Testet den reinen, zustandslosen Helfer, der CLI-Argumente (raw_underlying / raw_wrapper)
auf (Underlying, Wrapper) abbildet — ohne sys.argv, ohne I/O.

Abgedeckte Fälle:
- Legacy-Wert "equity"        → (EQUITY, SINGLE)
- Legacy-Wert "etf"           → (EQUITY_INDEX, FUND)
- Legacy-Wert "bond"          → (BOND, SINGLE)
- Neuer Stil ("equity_index", "fund") → (EQUITY_INDEX, FUND)
- None (kein Argument)        → Default (EQUITY, SINGLE)
- Ungültiger Wert "bogus"     → ValueError
"""
import pytest

from app.main import _resolve_taxonomy
from core.domain.taxonomy import Underlying, Wrapper


def test_legacy_equity():
    """'equity' ist ein Legacy-Wert → wird via legacy_to_taxonomy gemappt."""
    assert _resolve_taxonomy("equity", None) == (Underlying.EQUITY, Wrapper.SINGLE)


def test_legacy_etf():
    """'etf' ist ein Legacy-Wert → equity_index/fund (behebt den alten ETF-Durchfall)."""
    assert _resolve_taxonomy("etf", None) == (Underlying.EQUITY_INDEX, Wrapper.FUND)


def test_legacy_bond():
    """'bond' ist ein Legacy-Wert → bond/single."""
    assert _resolve_taxonomy("bond", None) == (Underlying.BOND, Wrapper.SINGLE)


def test_new_form_equity_index_fund():
    """Neuer Stil: raw_underlying='equity_index', raw_wrapper='fund' → (EQUITY_INDEX, FUND)."""
    assert _resolve_taxonomy("equity_index", "fund") == (Underlying.EQUITY_INDEX, Wrapper.FUND)


def test_none_defaults_to_equity_single():
    """raw_underlying=None → Default (EQUITY, SINGLE), kein Fehler."""
    assert _resolve_taxonomy(None, None) == (Underlying.EQUITY, Wrapper.SINGLE)


def test_invalid_raises_value_error():
    """Unbekannter Wert → ValueError (wird vom main()-Aufrufer abgefangen und als Exit-1 angezeigt)."""
    with pytest.raises(ValueError):
        _resolve_taxonomy("bogus", None)
