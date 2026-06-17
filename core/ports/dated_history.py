from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class DatedHistoryPort(ABC):
    """Datierte Zeitreihen-Historie: speichert Werte pro (Serie, Beobachtungsdatum)
    und erlaubt zeitbezogene Abfragen. Das konkrete Persistenz-Detail (Datei, DB,
    In-Memory) liegt im Adapter — der Domaenen-Kern kennt nur diese Schnittstelle.
    """

    @abstractmethod
    def append(self, series: str, observation_date: date, value: float) -> None:
        """Idempotent pro (series, observation_date): gleicher Tag ueberschreibt,
        haengt nicht doppelt an."""
        ...

    @abstractmethod
    def values(self, series: str) -> list[tuple[date, float]]:
        """Chronologisch sortiert."""
        ...

    @abstractmethod
    def value_on_or_before(self, series: str, target: date) -> Optional[float]:
        ...

    @abstractmethod
    def latest(self, series: str) -> Optional[tuple[date, float]]:
        ...
