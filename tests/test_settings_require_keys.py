"""`require_keys()`: Pflicht-API-Keys werden erst beim App-Start verlangt, NICHT beim Import.

Hintergrund: `config/settings.py` prüfte die Pflicht-Keys (FRED + ANTHROPIC) früher beim
**Import** (`raise EnvironmentError`, sobald einer fehlt). Folge: Die CI musste Dummy-Keys
setzen und jedes Testmodul, das `config` (direkt oder transitiv über `app.main`) importiert,
brauchte sie. Die Prüfung lebt jetzt in `require_keys()`, die nur die echten Einstiegspunkte
(`app.main`/`server`/`replay`/`calibrate`, `background_runner`) beim Start aufrufen. So bleibt
`config` importierbar (Tests/CI brauchen keine echten Keys — alle Datenquellen sind über Ports
gemockt), während echte Läufe weiter **fail-fast** abbrechen, wenn ein Pflicht-Key fehlt.
"""
import importlib

import pytest

import config.settings as settings


def test_import_ohne_pflichtkeys_wirft_nicht(monkeypatch):
    """Reload von config.settings ohne FRED/ANTHROPIC darf NICHT abbrechen.

    Vor dem Fix bricht der Import-Zeit-`raise` hier mit EnvironmentError ab (Rot);
    nach dem Fix lebt die Pflichtprüfung in require_keys() und der Import läuft durch.
    `load_dotenv` wird neutralisiert, sonst lädt der Reload die echte lokale `.env` neu.
    """
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        importlib.reload(settings)                 # vor dem Fix: EnvironmentError
        assert settings.FRED_API_KEY == ""
        assert settings.ANTHROPIC_API_KEY == ""
        assert hasattr(settings, "require_keys")
    finally:
        # Echten Modulzustand (aus der lokalen .env) für Folgetests wiederherstellen.
        monkeypatch.undo()
        importlib.reload(settings)


def test_require_keys_ok_wenn_vorhanden(monkeypatch):
    monkeypatch.setattr(settings, "FRED_API_KEY", "x")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "y")
    settings.require_keys()  # kein Raise


def test_require_keys_wirft_wenn_fred_fehlt(monkeypatch):
    monkeypatch.setattr(settings, "FRED_API_KEY", "")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "y")
    with pytest.raises(EnvironmentError, match="FRED_API_KEY"):
        settings.require_keys()


def test_require_keys_wirft_wenn_anthropic_fehlt(monkeypatch):
    monkeypatch.setattr(settings, "FRED_API_KEY", "x")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        settings.require_keys()


def test_require_keys_nennt_beide_fehlenden(monkeypatch):
    # Beide Pflicht-Keys leer → Meldung nennt beide (eine klare, vollständige Fehlermeldung).
    monkeypatch.setattr(settings, "FRED_API_KEY", "")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    with pytest.raises(EnvironmentError) as exc:
        settings.require_keys()
    msg = str(exc.value)
    assert "FRED_API_KEY" in msg and "ANTHROPIC_API_KEY" in msg
