import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY      = os.getenv("FRED_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FINNHUB_API_KEY   = os.getenv("FINNHUB_API_KEY", "")
FMP_API_KEY       = os.getenv("FMP_API_KEY", "")  # Financial Modeling Prep (LME-Metalle, EU/CH-CAPE)

# Daten-Caching-Schicht: wie viele Tage ein persistierter Rohdaten-Snapshot ohne
# Live-Nachziehen wiederverwendet wird (Dedup ZWISCHEN Läufen). Default 1 =
# Wiederverwendung nur am selben Kalendertag. Innerhalb EINES Laufs garantiert
# ohnehin das In-Lauf-Memo Konsistenz (unabhängig von diesem Wert).
SNAPSHOT_TTL_DAYS = int(os.getenv("SNAPSHOT_TTL_DAYS", "1"))

# Pflicht-Keys: ohne diese kann KEIN echter Lauf seine Daten-/LLM-Adapter aufbauen.
# (FINNHUB/FMP sind optional — nur einzelne Pfade brauchen sie, Defaults fangen das ab.)
_REQUIRED_KEYS = ("FRED_API_KEY", "ANTHROPIC_API_KEY")


def require_keys() -> None:
    """Verlangt die Pflicht-API-Keys (FRED + ANTHROPIC) — **beim tatsächlichen App-Start**
    aufrufen, NICHT beim Import.

    Warum nicht beim Import: `import config.settings` läuft auch in jedem Test und in der CI.
    Bräche der Import ohne echte Keys ab, müssten Tests/CI Dummy-Keys setzen, obwohl alle
    Datenquellen über Hexagonal-Ports gemockt sind und die Keys nie für echte Calls nutzen.
    Stattdessen rufen nur die echten Einstiegspunkte (`app.main`/`replay`/`calibrate`,
    `background_runner`) bzw. der echte Adapter-Aufbau (`app.server.make_orchestrator`)
    diese Funktion auf → echte Läufe brechen weiter **fail-fast** und mit klarer Meldung ab,
    Tests/CI bleiben keyfrei lauffähig.

    Liest die aktuellen Modul-Konstanten (per `globals()`), nicht eine zur Importzeit
    eingefrorene Kopie — so greifen `monkeypatch.setattr(settings, ...)` in Tests sauber.
    """
    missing = [name for name in _REQUIRED_KEYS if not globals().get(name)]
    if missing:
        raise EnvironmentError(f"{', '.join(missing)} fehlt in .env")
