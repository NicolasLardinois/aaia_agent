"""TDD: _is_fresh muss tz-aware UND alte naive _saved_at-Stempel vertragen.

Nach der utcnow→now(timezone.utc)-Umstellung schreibt der Cache `_saved_at`
tz-aware (mit `+00:00`). Alte Cache-Dateien tragen aber noch **naive** Stempel.
`_is_fresh` darf beide vergleichen, ohne am `naiv - aware`-TypeError zu scheitern.
"""
import json
from datetime import datetime, timedelta, timezone

import adapters.cache.result_cache as rc


def _write(path, saved_at_iso):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"_saved_at": saved_at_iso, "x": 1}, f)


def test_frisch_bei_tz_aware_stempel(tmp_path):
    p = str(tmp_path / "c.json")
    _write(p, datetime.now(timezone.utc).isoformat())   # neues Format (+00:00)
    assert rc._is_fresh(p) is True


def test_frisch_bei_altem_naivem_stempel(tmp_path):
    """Rückwärtskompatibel: ein naiver (alter) Stempel von 'jetzt' gilt als frisch."""
    p = str(tmp_path / "c.json")
    _write(p, datetime.utcnow().isoformat())            # altes Format (ohne tz)
    assert rc._is_fresh(p) is True


def test_veraltet_bei_altem_stempel(tmp_path):
    p = str(tmp_path / "c.json")
    old = datetime.now(timezone.utc) - timedelta(hours=5)
    _write(p, old.isoformat())
    assert rc._is_fresh(p) is False


def test_fehlt_datei_nicht_frisch(tmp_path):
    assert rc._is_fresh(str(tmp_path / "gibt-es-nicht.json")) is False
