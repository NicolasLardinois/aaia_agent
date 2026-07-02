from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Optional


class SnapshotStore(ABC):
    """Datierter Key-Value-Store hinter den Caching-Decorators.

    ``value`` ist JSON-serialisierbar: entweder ein Skalar (float) ODER ein
    codierter Payload (z. B. ein per ``dataframe_codec`` serialisierter DataFrame).
    Die Datums-Semantik ist bewusst identisch zu ``DatedHistoryPort``: ``get``
    liefert den frischesten Wert mit ``obs_date <= as_of`` (Point-in-Time-fähig).
    """

    @abstractmethod
    def put(self, namespace: str, key: str, obs_date: date, value: Any) -> None:
        """Idempotent pro (namespace, key, obs_date): gleicher Tag überschreibt."""
        ...

    @abstractmethod
    def get(self, namespace: str, key: str, as_of: date) -> Optional[tuple[date, Any]]:
        """(obs_date, value) des frischesten Eintrags mit obs_date <= as_of; None wenn leer."""
        ...
