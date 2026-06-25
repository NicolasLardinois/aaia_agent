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

from app.main import _is_legacy_call, _resolve_taxonomy, _usage
from core.domain.taxonomy import (
    Underlying, Wrapper, underlying_choices, wrapper_choices,
)


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


# --- CLI-Härtung (Review PR #37): Legacy↔neu-Überlappung + getrennte Fehlertexte ---

def test_commodity_with_explicit_single_overrides_legacy_future():
    """Bugfix (a): 'commodity single' ist neuer Stil → (COMMODITY, SINGLE).

    Vorher wurde 'commodity' als Legacy abgefangen und stillschweigend auf FUTURE
    gezwungen (legacy_to_taxonomy('commodity') → FUTURE), 'single' rutschte in den Sektor.
    Ab Phase 2 zählt der Wrapper → ein explizit gesetzter Wrapper muss respektiert werden.
    """
    assert _resolve_taxonomy("commodity", "single") == (Underlying.COMMODITY, Wrapper.SINGLE)


def test_commodity_with_explicit_future():
    """'commodity future' (neuer Stil) → (COMMODITY, FUTURE) — Wrapper explizit gesetzt."""
    assert _resolve_taxonomy("commodity", "future") == (Underlying.COMMODITY, Wrapper.FUTURE)


def test_precious_metal_with_physical_etc():
    """'precious_metal physical_etc' → physisch hinterlegtes ETC (reiner Spot), nicht FUTURE."""
    assert _resolve_taxonomy("precious_metal", "physical_etc") == (
        Underlying.PRECIOUS_METAL, Wrapper.PHYSICAL_ETC)


def test_commodity_without_wrapper_keeps_legacy_future():
    """Rückwärtskompatibel: 'commodity' ohne Wrapper bleibt Legacy-Default (COMMODITY, FUTURE).

    Historische Annahme: ein nacktes Rohstoff-Exposure läuft i. d. R. über Futures.
    Nur ein explizit gesetzter, gültiger Wrapper schaltet auf den neuen Stil um.
    """
    assert _resolve_taxonomy("commodity", None) == (Underlying.COMMODITY, Wrapper.FUTURE)


def test_commodity_with_sector_like_token_stays_legacy():
    """'commodity Energy' — 'Energy' ist kein gültiger Wrapper → Legacy (COMMODITY, FUTURE).

    Sektor-Strings (Energy/Technology/…) kollidieren nie mit Wrapper-Namen, deshalb darf
    ein Nicht-Wrapper-Token den alten Legacy-Pfad (Sektor an pos[3]) nicht zerstören.
    """
    assert _resolve_taxonomy("commodity", "Energy") == (Underlying.COMMODITY, Wrapper.FUTURE)


def test_invalid_wrapper_error_names_wrapper():
    """Bugfix (b): ungültiger Wrapper bei gültigem underlying → Fehlertext nennt *wrapper*.

    Vorher meldete 'bottomup AAPL equity_index Technology' fälschlich
    'unbekannter underlying-Wert' — obwohl equity_index gültig ist und Technology der
    ungültige Wrapper war.
    """
    with pytest.raises(ValueError, match="wrapper"):
        _resolve_taxonomy("equity_index", "Technology")


def test_invalid_underlying_error_names_underlying():
    """Ungültiges underlying → Fehlertext nennt *underlying* (klar getrennt vom Wrapper-Fall)."""
    with pytest.raises(ValueError, match="underlying"):
        _resolve_taxonomy("bogus", None)


# --- _is_legacy_call: steuert auch den Positions-Offset in main() (sector-Spalte) ---

def test_is_legacy_call_legacy_only_token():
    """'etf'/'index' haben kein neues Äquivalent → immer Legacy."""
    assert _is_legacy_call("etf", None) is True
    assert _is_legacy_call("index", None) is True


def test_is_legacy_call_overlap_with_wrapper_is_new_style():
    """Überlappender Token + gültiger Wrapper → neuer Stil (nicht Legacy)."""
    assert _is_legacy_call("commodity", "future") is False


def test_is_legacy_call_overlap_without_wrapper_is_legacy():
    """Überlappender Token ohne Wrapper bzw. mit Sektor-Token → Legacy."""
    assert _is_legacy_call("commodity", None) is True
    assert _is_legacy_call("commodity", "Energy") is True


def test_is_legacy_call_new_only_and_none():
    """'equity_index' = neuer Stil; None = kein Argument → kein Legacy."""
    assert _is_legacy_call("equity_index", "fund") is False
    assert _is_legacy_call(None, None) is False


# --- DRY: erlaubte Werte aus den Enums ableiten (Review PR #41, Single Source) ---
# Bisher standen die erlaubten underlying-/wrapper-Werte als hartkodierter Text in den
# ValueErrors UND im Usage-Block — driften still, wenn ein Enum-Wert ergänzt wird.
# Die folgenden Tests verankern: jeder Enum-Wert MUSS in den abgeleiteten Listen, in
# den Fehlertexten und im Usage-Text auftauchen (sonst bräche bei einem neuen Enum-Wert
# genau ein Test → der hartkodierte Text fällt auf).

def test_underlying_choices_pipe_separated_in_enum_order():
    assert underlying_choices() == " | ".join(u.value for u in Underlying)


def test_wrapper_choices_pipe_separated_in_enum_order():
    assert wrapper_choices() == " | ".join(w.value for w in Wrapper)


def test_choices_contain_every_enum_value():
    for u in Underlying:
        assert u.value in underlying_choices()
    for w in Wrapper:
        assert w.value in wrapper_choices()


def test_unknown_underlying_error_lists_every_underlying_value():
    """Der underlying-Fehlertext nennt jeden gültigen Wert (aus dem Enum abgeleitet)."""
    with pytest.raises(ValueError) as exc:
        _resolve_taxonomy("bogus", "single")
    msg = str(exc.value)
    for u in Underlying:
        assert u.value in msg


def test_unknown_wrapper_error_lists_every_wrapper_value():
    """Der wrapper-Fehlertext nennt jeden gültigen Wert (aus dem Enum abgeleitet).

    'equity_index' ist KEIN Überlappungs-Token → mit ungültigem Wrapper läuft es in
    den Wrapper-Validierungszweig (nicht in den Legacy-Pfad)."""
    with pytest.raises(ValueError) as exc:
        _resolve_taxonomy("equity_index", "bogus")
    msg = str(exc.value)
    for w in Wrapper:
        assert w.value in msg


def test_usage_text_lists_every_underlying_and_wrapper_value():
    """Der CLI-Usage-Text (gedruckt bei Fehlbedienung) listet alle Enum-Werte."""
    text = _usage()
    for e in list(Underlying) + list(Wrapper):
        assert e.value in text
