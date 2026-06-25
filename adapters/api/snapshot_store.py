"""Persistiert das letzte serialisierte Cockpit-Snapshot-Dict auf Disk.

Warum: `RunManager._latest` (das Domaenen-Ergebnis) liegt nur im Arbeitsspeicher
und ist nach einem Server-Neustart weg — GET /api/cockpit lieferte dann wieder
204 (kein Ergebnis), bis ein neuer Lauf durchlief. Wir legen daher das bereits
serialisierte Dict (cockpit_to_dict) auf Disk ab und laden es beim Start.

Bewusst wird das DICT persistiert, nicht das Domaenen-Objekt: Die Serialisierung
ist verlustbehaftet (flacht/aggregiert), eine verlustfreie Rueck-Konstruktion des
CockpitResult aus JSON gibt es nicht. Der persistierte Snapshot wird daher direkt
ausgeliefert.

Defensiv wie JsonDatedHistory: fehlende oder korrupte Datei -> None statt Crash;
Schreiben atomar (temp-Datei + os.replace), damit ein abgebrochener Schreibvorgang
keine halbe Datei hinterlaesst.
"""
import json
import logging
import os
import tempfile

_logger = logging.getLogger(__name__)


class JsonCockpitSnapshotStore:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> dict | None:
        """Liest den persistierten Snapshot; None wenn Datei fehlt, korrupt ist
        oder die oberste Ebene kein Objekt (dict) ist."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            _logger.warning("Cockpit-Snapshot konnte nicht geladen werden: %s", self._path)
            return None
        return data if isinstance(data, dict) else None

    def save(self, snapshot: dict) -> None:
        """Schreibt den Snapshot atomar; Fehler werden nur geloggt (ein gescheitertes
        Persistieren darf den Lauf nicht abstuerzen lassen)."""
        try:
            directory = os.path.dirname(self._path) or "."
            os.makedirs(directory, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f)
                os.replace(tmp, self._path)
            except OSError:
                # Temp-Datei aufraeumen, falls der Tausch scheiterte
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise
        except OSError:
            _logger.warning("Cockpit-Snapshot konnte nicht gespeichert werden: %s", self._path)
