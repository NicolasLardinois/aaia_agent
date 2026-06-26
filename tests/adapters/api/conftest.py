"""API-Paket-Test-Vorkehrung.

Die früher hier lokale `_auth_off_by_default`-Fixture (leerte `AAIA_ACCESS_TOKEN`
und `RENDER` je Test, damit token-lose Routen-Tests deterministisch Auth-AUS sehen)
ist nach `tests/conftest.py` gewandert und gilt jetzt **session-weit** — sie heilt
die `load_dotenv()`-Import-Verschmutzung für jedes Modul, nicht nur dieses Paket
(siehe Doku der `_neutralize_ambient_secrets`-Fixture dort).

Tests, die Auth EIN oder das Render-Fail-closed-Verhalten prüfen, setzen
`AAIA_ACCESS_TOKEN`/`RENDER` weiterhin selbst per `monkeypatch.setenv(...)`; ihr
`monkeypatch` läuft NACH den autouse-Fixtures → sie gewinnen. Diese Datei bleibt als
Paket-Marker und Fundstelle der Begründung erhalten (kein eigener Fixture-Code mehr).
"""
