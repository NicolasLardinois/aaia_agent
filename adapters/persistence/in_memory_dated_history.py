from datetime import date
from typing import Optional

from core.ports.dated_history import DatedHistoryPort


class InMemoryDatedHistory(DatedHistoryPort):
    """In-Memory-Umsetzung von DatedHistoryPort (ohne Persistenz).

    Praktisch fuer Tests und zum Umhuellen einer vom Provider gelieferten
    datierten Reihe (kein Datei-I/O, kein prozessuebergreifender Zustand).
    """

    def __init__(self, data: Optional[dict[str, list[tuple[date, float]]]] = None) -> None:
        self._data: dict[str, dict[str, float]] = {}
        if data:
            for series, observations in data.items():
                for observation_date, value in observations:
                    self.append(series, observation_date, value)

    def append(self, series: str, observation_date: date, value: float) -> None:
        self._data.setdefault(series, {})[observation_date.isoformat()] = value

    def values(self, series: str) -> list[tuple[date, float]]:
        entries = self._data.get(series, {})
        return [
            (date.fromisoformat(d), v)
            for d, v in sorted(entries.items())
        ]

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
