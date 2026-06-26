"""Tests für den geteilten Fehler-Schutz-Helfer `core/utils/safe.py`.

Hintergrund (AGENTS.md §2 „Defensive Aggregation"): Nach
`asyncio.gather(..., return_exceptions=True)` ist ein Teilergebnis entweder der echte
Wert ODER eine als Wert zurückgegebene Exception. Dieses Entpacken „Exception → neutraler
Default" ist heute in ~23 Dateien lokal als `def _safe(r, d)` / `def _safe(v)` dupliziert.
`safe_result` / `safe_provider_call` vereinheitlichen das an EINER Stelle und legen
optionales Logging hinein (Befund 2: stiller Ausfall ist sonst nicht von „echt nichts da"
unterscheidbar). Diese Tests fixieren das Verhalten, bevor der projektweite Rollout beginnt.
"""
import asyncio
import logging

import pytest

from core.utils.safe import safe_result, safe_provider_call


# ───────────────────────── safe_result (gather-Entpackung) ─────────────────────────

def test_safe_result_gibt_wert_unveraendert_zurueck():
    assert safe_result(42, default=0) == 42
    assert safe_result("ok", default="x") == "ok"
    assert safe_result({"a": 1}, default={}) == {"a": 1}


def test_safe_result_falsy_werte_sind_keine_fehler():
    # 0, "", None, [] sind gültige Ergebnisse — NICHT durch den Default ersetzen.
    assert safe_result(0, default=99) == 0
    assert safe_result("", default="d") == ""
    assert safe_result(None, default="d") is None
    assert safe_result([], default=[1]) == []


def test_safe_result_exception_liefert_default():
    assert safe_result(ValueError("kaputt"), default=0) == 0
    assert safe_result(RuntimeError(), default=None) is None
    assert safe_result(KeyError("x"), default={}) == {}


def test_safe_result_base_exception_wird_nicht_verschluckt():
    # CancelledError ist BaseException, NICHT Exception → wie das bestehende
    # `isinstance(r, Exception)` NICHT zum Default machen (Abbruch nicht maskieren).
    cancelled = asyncio.CancelledError()
    assert safe_result(cancelled, default=0) is cancelled


def test_safe_result_loggt_bei_label(caplog):
    with caplog.at_level(logging.WARNING):
        out = safe_result(ValueError("boom"), default=0, label="insider-Agent für AAPL")
    assert out == 0
    assert "insider-Agent für AAPL" in caplog.text


def test_safe_result_loggt_nicht_ohne_label(caplog):
    # Ohne label rückwärtskompatibel still (bestehende Aufrufer ändern ihr Verhalten nicht).
    with caplog.at_level(logging.WARNING):
        out = safe_result(ValueError("boom"), default=0)
    assert out == 0
    assert caplog.text == ""


def test_safe_result_loggt_nicht_im_erfolgsfall(caplog):
    with caplog.at_level(logging.WARNING):
        safe_result(7, default=0, label="x")
    assert caplog.text == ""


# ───────────────────────── safe_provider_call (Einzel-Call-Wrapper) ─────────────────────────

def test_safe_provider_call_gibt_ergebnis_zurueck():
    async def ok():
        return 123

    assert asyncio.run(safe_provider_call(ok, default=0)) == 123


def test_safe_provider_call_faengt_geworfene_exception_ab():
    async def boom():
        raise RuntimeError("API kaputt")

    assert asyncio.run(safe_provider_call(boom, default=-1)) == -1


def test_safe_provider_call_reicht_argumente_durch():
    async def add(a, b, *, c=0):
        return a + b + c

    assert asyncio.run(safe_provider_call(add, 2, 3, c=4, default=0)) == 9


def test_safe_provider_call_loggt_bei_label(caplog):
    async def boom():
        raise ValueError("xx")

    with caplog.at_level(logging.WARNING):
        out = asyncio.run(safe_provider_call(boom, default=None, label="FRED-Call"))
    assert out is None
    assert "FRED-Call" in caplog.text


def test_safe_provider_call_loggt_nicht_ohne_label(caplog):
    async def boom():
        raise ValueError("xx")

    with caplog.at_level(logging.WARNING):
        asyncio.run(safe_provider_call(boom, default=None))
    assert caplog.text == ""
