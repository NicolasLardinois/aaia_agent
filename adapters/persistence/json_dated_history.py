import json
import logging
import os
from datetime import date
from typing import Optional

from core.ports.dated_history import DatedHistoryPort

logger = logging.getLogger(__name__)


class JsonDatedHistory(DatedHistoryPort):
    """JSON-datei-gestuetzte Umsetzung von DatedHistoryPort.

    Ersetzt prozess-globalen In-Memory-State (_RATE_HISTORY, regime-History).
    Persistenzformat: {series: {ISO-Datum: value}}.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._data: dict[str, dict[str, float]] = self._load()

    def _load(self) -> dict[str, dict[str, float]]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _save(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f)

    def append(self, series: str, observation_date: date, value: float) -> None:
        self._data.setdefault(series, {})[observation_date.isoformat()] = value
        self._save()

    def values(self, series: str) -> list[tuple[date, float]]:
        # Defensiv gegen korrumpierte Persistenz: ein unparsebares Datum oder ein
        # nicht-numerischer Wert wird uebersprungen (+ Warn-Log), statt die ganze
        # Serie mit einer Exception beim Aufrufer zu sprengen. Werte werden
        # einheitlich zu float gecastet (JSON kennt int und float).
        entries = self._data.get(series, {})
        out: list[tuple[date, float]] = []
        for d, v in sorted(entries.items()):
            try:
                parsed_date = date.fromisoformat(d)
                parsed_value = float(v)
            except (ValueError, TypeError):
                logger.warning("JsonDatedHistory: ueberspringe korrupten Eintrag %r=%r in Serie %r (%s)",
                               d, v, series, self.path)
                continue
            out.append((parsed_date, parsed_value))
        return out

    def value_on_or_before(self, series: str, target: date) -> Optional[float]:
        result: Optional[float] = None
        for d, v in self.values(series):
            if d <= target:
                result = v
            else:
                break
        return result

    def latest(self, series: str) -> Optional[tuple[date, float]]:
        vals = self.values(series)
        return vals[-1] if vals else None
