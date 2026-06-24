"""Hermetische Test-Vorkehrung fuer das gesamte API-Paket: Auth standardmaessig AUS.

Hintergrund (Test-Verschmutzung): `config/settings.py` ruft beim **Import**
`load_dotenv()` auf. Enthaelt die lokale `.env` ein `AAIA_ACCESS_TOKEN`, landet
es prozessweit in `os.environ`, sobald irgendein Modul `config.settings`
importiert. Im **Gesamtlauf** zieht pytest bei der Collection alle Testmodule
(u. a. `tests/test_cli_* -> app.main -> config.settings`) -> Token gesetzt,
auch wenn die betroffenen Tests gar nicht laufen. Folge: token-lose Routen-Tests
bekommen `401` statt `204/202` -- aber NUR im Gesamtlauf, nicht in Isolation
(Collection-/Reihenfolge-Abhaengigkeit).

Diese `autouse`-Fixture stellt fuer JEDEN Test im API-Paket einen bekannten,
sauberen Ausgangszustand her und macht so alle API-Tests unabhaengig vom
Ambient-Env (sie ersetzt die fruehere, nur in `test_routes_cockpit.py` lokale
`_auth_disabled`-Fixture und deckt nun auch `test_routes_auth.py` /
`test_app_factory_token_guard.py` mit ab):

- `AAIA_ACCESS_TOKEN` wird geleert -> Auth ist aus (dokumentierter Backend-Test-
  Default). Tests, die Auth EIN brauchen, setzen das Token selbst per
  `monkeypatch.setenv(...)`; ihr `monkeypatch` laeuft NACH dieser Fixture ->
  sie gewinnen.
- `RENDER` wird ebenfalls geleert: bei *leerem* Token UND gesetztem `RENDER`
  wirft `create_app` bewusst `RuntimeError` (Fail-closed in Produktion, siehe
  `app_factory.py`). In einem Ambient-Env mit `RENDER` (z. B. Suite-Lauf auf
  einer Render-Shell) wuerden die token-losen Tests sonst crashen statt gruen zu
  sein. Tests, die das Fail-closed-Verhalten pruefen, setzen `RENDER` selbst.

Spiegelt das Muster der globalen Netz-Block-Fixture in `tests/conftest.py`.
"""
import pytest


@pytest.fixture(autouse=True)
def _auth_off_by_default(monkeypatch):
    # Ambient/aus `.env` geladene Werte neutralisieren -> deterministisch Auth aus.
    monkeypatch.delenv("AAIA_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
