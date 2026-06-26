"""Globale Test-Vorkehrungen: (1) ECHTES Netzwerk deaktivieren, (2) sicherheits-
relevante Ambient-Env-Variablen session-weit neutralisieren.

(1) Netz-Block: Einige Agenten machen (noch) **hardcoded** I/O — `requests.get`
(CBOE / World-Bank / FMP) bzw. `yfinance.Ticker` — statt über injizierte Ports
(Verstoß gegen AGENTS.md §1; eigener Refactor-PR ist im Logbuch festgehalten).
Ohne Mock hängt ein solcher Call in der CI (kein/blockiertes Netz) und blockierte
zuvor die ganze Suite (bis ~GH-Actions-Maximum).

Diese `autouse`-Fixture blockt das Netz **global**: `requests`/`yfinance` werfen →
die **defensiven** `except Exception`-Pfade der Agenten liefern ihre Defaults
(UNAVAILABLE / None / 1.0). Damit ist die Suite offline-sicher, ohne in jedem
betroffenen Test einzeln zu mocken. Tests, die ihre Datenquelle selbst mocken,
überschreiben dies (ihr `monkeypatch` läuft NACH dieser Fixture → gewinnt).

(2) Env-Hermetik: `config/settings.py` ruft beim **Import** `load_dotenv()` auf.
Enthält die lokale `.env` ein `AAIA_ACCESS_TOKEN` (oder ist `RENDER` ambient
gesetzt), landet das prozessweit in `os.environ`, sobald **irgendein** Testmodul
`config.settings` importiert (bei der Collection u. a. via `app.main`). Folge: token-
lose Routen-Tests bekamen im **Gesamtlauf** `401` statt `204/202` — aber nur dort,
nicht in Isolation (Collection-/Reihenfolge-Abhängigkeit, PR #47). Die zweite
`autouse`-Fixture leert diese Variablen je Test **session-weit**, sodass jedes
Modul — nicht nur das API-Paket — einen sauberen Ausgangszustand hat. Tests, die
Auth EIN oder `RENDER` brauchen, setzen sie selbst (`monkeypatch.setenv(...)` läuft
NACH dieser Fixture → gewinnt). Das löst die zuvor nur im API-Paket lokale
`_auth_off_by_default`-Fixture session-weit ab.
"""
import pytest

# Ambient-Variablen, die in keinem Test ungewollt aus der lokalen `.env` durchschlagen
# dürfen (sonst Reihenfolge-abhängige Flakes wie in PR #47). Tests, die sie brauchen,
# setzen sie explizit selbst.
_NEUTRALIZED_ENV = ("AAIA_ACCESS_TOKEN", "RENDER")


def _blocked(*args, **kwargs):
    raise RuntimeError(
        "Echtes Netzwerk in Tests ist deaktiviert (tests/conftest.py). "
        "Mocke die Datenquelle (Port/Adapter) statt echtem requests/yfinance.")


@pytest.fixture(autouse=True)
def _disable_real_network(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _blocked, raising=False)
    monkeypatch.setattr(requests, "post", _blocked, raising=False)
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: _blocked(), raising=False)
    monkeypatch.setattr(requests.Session, "post", lambda self, *a, **k: _blocked(), raising=False)

    import yfinance
    monkeypatch.setattr(yfinance, "Ticker", _blocked, raising=False)


@pytest.fixture(autouse=True)
def _neutralize_ambient_secrets(monkeypatch):
    # Sicherheitsrelevante Ambient/`.env`-Variablen je Test leeren → deterministischer
    # Ausgangszustand (Auth-Default AUS, kein Render-Fail-closed). Tests überschreiben selbst.
    for var in _NEUTRALIZED_ENV:
        monkeypatch.delenv(var, raising=False)
