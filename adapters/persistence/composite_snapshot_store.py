import json
import logging
import os
from datetime import date
from typing import Any, Optional

from core.ports.dated_history import DatedHistoryPort
from core.ports.snapshot_store import SnapshotStore

_log = logging.getLogger(__name__)


def _is_scalar(value: Any) -> bool:
    # bool ist Subklasse von int, soll aber NICHT als float-Zeitreihe gelten.
    # int wird absichtlich als numerischer Skalar behandelt (über float() koerziert).
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class CompositeSnapshotStore(SnapshotStore):
    """SnapshotStore, der nach Wert-Typ routet (Review-Entscheid 2026-07-01):

    - **float → DatedHistoryPort** (Wiederverwendung; Serie ``f"{namespace}:{key}"``).
      Kein zweiter Zeitreihen-Store; der Backtest-Fall fällt geschenkt ab.
    - **Payload (str/dict/…) → JSON-Blob-Datei** (datiert), da DatedHistoryPort nur floats hält.
    """

    def __init__(self, scalar_history: DatedHistoryPort, blob_path: str) -> None:
        self._scalars = scalar_history
        self._blob_path = blob_path
        self._blobs: dict[str, dict[str, Any]] = self._load_blobs()

    @staticmethod
    def _series(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def _load_blobs(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self._blob_path):
            return {}
        try:
            with open(self._blob_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return raw if isinstance(raw, dict) else {}
        except Exception as exc:
            _log.warning("CompositeSnapshotStore: Blob-Datei nicht lesbar, starte leer (%s)", exc)
            return {}

    def _save_blobs(self) -> None:
        directory = os.path.dirname(self._blob_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self._blob_path, "w", encoding="utf-8") as f:
            json.dump(self._blobs, f)

    def put(self, namespace: str, key: str, obs_date: date, value: Any) -> None:
        series = self._series(namespace, key)
        if _is_scalar(value):
            self._scalars.append(series, obs_date, float(value))
        else:
            self._blobs.setdefault(series, {})[obs_date.isoformat()] = value
            try:
                self._save_blobs()
            except Exception as exc:  # Best effort: Persistenz-Fehler killt den Lauf nicht.
                _log.warning("CompositeSnapshotStore: Blob-Save fehlgeschlagen (%s)", exc)

    def get(self, namespace: str, key: str, as_of: date) -> Optional[tuple[date, Any]]:
        series = self._series(namespace, key)
        # 1. Skalar-Zweig (DatedHistoryPort) — frischester mit d <= as_of.
        scalar_hit: Optional[tuple[date, Any]] = None
        for d, v in self._scalars.values(series):
            if d <= as_of:
                scalar_hit = (d, v)
            else:
                break
        if scalar_hit is not None:
            return scalar_hit
        # 2. Blob-Zweig — analog.
        blob_hit: Optional[tuple[date, Any]] = None
        for iso, v in sorted(self._blobs.get(series, {}).items()):
            d = date.fromisoformat(iso)
            if d <= as_of:
                blob_hit = (d, v)
            else:
                break
        return blob_hit
