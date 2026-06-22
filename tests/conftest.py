"""Globale Test-Vorkehrung: ECHTES Netzwerk in Tests deaktivieren.

Hintergrund: Einige Agenten machen (noch) **hardcoded** I/O — `requests.get`
(CBOE / World-Bank / FMP) bzw. `yfinance.Ticker` — statt über injizierte Ports
(Verstoß gegen AGENTS.md §1; eigener Refactor-PR ist im Logbuch festgehalten).
Ohne Mock hängt ein solcher Call in der CI (kein/blockiertes Netz) und blockierte
zuvor die ganze Suite (bis ~GH-Actions-Maximum).

Diese `autouse`-Fixture blockt das Netz **global**: `requests`/`yfinance` werfen →
die **defensiven** `except Exception`-Pfade der Agenten liefern ihre Defaults
(UNAVAILABLE / None / 1.0). Damit ist die Suite offline-sicher, ohne in jedem
betroffenen Test einzeln zu mocken. Tests, die ihre Datenquelle selbst mocken,
überschreiben dies (ihr `monkeypatch` läuft NACH dieser Fixture → gewinnt).
"""
import pytest


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
