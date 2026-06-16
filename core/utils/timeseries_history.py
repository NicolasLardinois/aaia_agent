import json
import os
from datetime import date


class DatedHistory:
    """JSON-datei-gestuetzte, datierte Zeitreihen-Historie.

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
        """Idempotent pro (series, observation_date): gleicher Tag
        ueberschreibt, haengt nicht doppelt an."""
        self._data.setdefault(series, {})[observation_date.isoformat()] = value
        self._save()

    def values(self, series: str) -> list[tuple[date, float]]:
        """Chronologisch sortiert."""
        entries = self._data.get(series, {})
        return [
            (date.fromisoformat(d), v)
            for d, v in sorted(entries.items())
        ]

    def value_on_or_before(self, series: str, target: date) -> float | None:
        result: float | None = None
        for d, v in self.values(series):
            if d <= target:
                result = v
            else:
                break
        return result

    def latest(self, series: str) -> tuple[date, float] | None:
        vals = self.values(series)
        return vals[-1] if vals else None
