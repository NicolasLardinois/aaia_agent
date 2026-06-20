import json
import logging
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.domain.models import ShortAction
from adapters.memory.supabase_memory import SupabaseMemory, _build_indicators_snapshot


def _result(short_action):
    """Minimaler DeepDiveResult-Stub für save_analysis (bottom_up=None überspringt den BU-Block)."""
    return SimpleNamespace(
        ticker="XYZ", asset_class="equity", market="USA",
        top_down_context="ctx", alignment="aligned_bearish", dominant_signal="BEARISH",
        recommendation=SimpleNamespace(action=SimpleNamespace(value="NONE")),
        confidence=0.7, xai_explanation="why",
        bottom_up=None, conflict_resolution=None,
        top_down_anomaly=None, bottom_up_anomaly=None,
        short_action=short_action,
    )


def test_save_analysis_persists_short_action(monkeypatch):
    """save_analysis muss die Short-Aktion separat persistieren (Spalte short_action),
    weil die Long-Linse bei Short-Positionen auf NONE deferiert und der echte
    COVER/HOLD-Wert sonst nie in der History landet."""
    cur = MagicMock()

    @contextmanager
    def fake_cursor():
        yield cur

    conn = MagicMock()
    conn.cursor.side_effect = fake_cursor

    @contextmanager
    def fake_connect(self):
        yield conn

    monkeypatch.setattr(SupabaseMemory, "_connect", fake_connect)

    mem = SupabaseMemory.__new__(SupabaseMemory)  # __init__ umgehen (kein SUPABASE_DB_URL nötig)
    mem.save_analysis(_result(ShortAction.COVER))

    sql, params = cur.execute.call_args.args
    assert "short_action" in sql, "INSERT muss die Spalte short_action enthalten"
    assert "COVER" in params, f"short_action-Wert COVER fehlt in den INSERT-Parametern: {params}"


# ── Bug #46: kein stilles `except AttributeError: pass` mehr ───────────────
# Fix-Ziele: (1) granular — ein umbenanntes/fehlendes Feld überspringt nur sich
# selbst, nicht alle folgenden Indikatoren; (2) beobachtbar — der Fehler wird
# geloggt statt still verschluckt (verwandt mit dem geplanten _safe-Helfer, §7).

def _result_with_bu(bu):
    r = _result(ShortAction.COVER)
    r.bottom_up = bu
    return r


def _save_and_capture(result, monkeypatch, cockpit=None):
    """Ruft save_analysis mit gemocktem _connect auf und gibt die INSERT-Parameter zurück."""
    cur = MagicMock()

    @contextmanager
    def fake_cursor():
        yield cur

    conn = MagicMock()
    conn.cursor.side_effect = fake_cursor

    @contextmanager
    def fake_connect(self):
        yield conn

    monkeypatch.setattr(SupabaseMemory, "_connect", fake_connect)
    mem = SupabaseMemory.__new__(SupabaseMemory)
    mem.save_analysis(result, cockpit=cockpit)
    _sql, params = cur.execute.call_args.args
    return params


def _broken_cockpit():
    """Cockpit, dessen sentiment-Felder fehlen (vix/fear_greed brechen),
    macro/yield_curve aber gültig sind — simuliert umbenannte Unterfelder."""
    return SimpleNamespace(
        sentiment=SimpleNamespace(),  # kein .vix / .fear_greed → AttributeError
        macro=SimpleNamespace(
            regime_confidence=0.8,
            inflation=SimpleNamespace(usa=SimpleNamespace(cpi=3.2)),
        ),
        yield_curve=SimpleNamespace(
            yield_spreads=SimpleNamespace(usa=SimpleNamespace(spread_10y2y=0.5)),
        ),
    )


def _bu_without_short_interest():
    """Bottom-Up-Ergebnis mit gültigen fundamentals/insider, aber fehlendem
    short_interest-Attribut — simuliert ein umbenanntes Feld."""
    return SimpleNamespace(
        valuation_range=None, index=None, precious_metals=None, commodity_deep=None,
        fundamentals=SimpleNamespace(pe_ratio=15.0),
        insider=SimpleNamespace(recent_transactions=3),
        # absichtlich KEIN short_interest-Attribut → simuliert umbenanntes Feld
    )


def _cockpit_without_regime():
    """Cockpit mit gültigem regime_confidence, aber fehlendem regime-Attribut."""
    return SimpleNamespace(
        sentiment=SimpleNamespace(),
        yield_curve=SimpleNamespace(),
        macro=SimpleNamespace(regime_confidence=0.6),  # KEIN regime-Attribut
    )


def test_build_snapshot_granular_keeps_later_fields_when_one_breaks():
    """Das gebrochene sentiment-Feld darf die späteren Indikatoren nicht mitreißen."""
    snap = _build_indicators_snapshot(_broken_cockpit())
    assert snap.get("inflation_cpi_usa") == 3.2
    assert snap.get("yield_spread_10y2y") == 0.5
    assert "vix" not in snap


def test_build_snapshot_logs_warning_instead_of_silent_swallow(caplog):
    """Ein fehlendes/umbenanntes Feld muss eine Warnung loggen, nicht still scheitern."""
    with caplog.at_level(logging.WARNING):
        _build_indicators_snapshot(_broken_cockpit())
    assert any(r.levelno == logging.WARNING for r in caplog.records), \
        "kein WARNING beim fehlgeschlagenen Feldzugriff (still verschluckt?)"


def test_save_analysis_bottom_up_block_is_granular(monkeypatch):
    """short_interest bricht, darf aber fundamentals/insider nicht mitreißen."""
    params = _save_and_capture(_result_with_bu(_bu_without_short_interest()), monkeypatch=monkeypatch)
    indicators = json.loads(params[-1])
    assert indicators.get("pe_ratio") == 15.0
    assert indicators.get("insider_transactions") == 3


def test_save_analysis_bottom_up_block_logs_warning(monkeypatch, caplog):
    """Das gebrochene short_interest-Feld muss eine Warnung loggen, nicht still scheitern."""
    with caplog.at_level(logging.WARNING):
        _save_and_capture(_result_with_bu(_bu_without_short_interest()), monkeypatch=monkeypatch)
    assert any(r.levelno == logging.WARNING and "short_float_pct" in r.getMessage()
               for r in caplog.records), \
        "kein WARNING für das gebrochene short_interest-Feld (still verschluckt?)"


def test_save_analysis_regime_block_is_granular(monkeypatch):
    """regime (params[3]) bricht, regime_confidence (params[4]) muss trotzdem durchkommen."""
    params = _save_and_capture(_result(ShortAction.COVER), cockpit=_cockpit_without_regime(), monkeypatch=monkeypatch)
    assert params[4] == 0.6


def test_save_analysis_regime_block_logs_warning(monkeypatch, caplog):
    """Das gebrochene regime-Feld muss eine Warnung loggen, nicht still scheitern."""
    with caplog.at_level(logging.WARNING):
        _save_and_capture(_result(ShortAction.COVER), cockpit=_cockpit_without_regime(), monkeypatch=monkeypatch)
    assert any(r.levelno == logging.WARNING and "'regime'" in r.getMessage()
               for r in caplog.records), \
        "kein WARNING für das gebrochene regime-Feld (still verschluckt?)"
