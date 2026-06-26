"""Port: CBOE-Total-Put/Call-Datenquelle für den Sentiment-Pfad.

Hexagonal (AGENTS.md §1): der Agent hängt nur von diesem ABC ab, nie von
`requests`/CBOE. Beide Methoden sind **synchron** (blockierendes I/O) — der
Agent wickelt sie in `asyncio.to_thread(...)`.
"""
from abc import ABC, abstractmethod


class PutCallSource(ABC):
    """Liefert den aktuellen CBOE-Total-Put/Call-Wert und eine Tageshistorie."""

    @abstractmethod
    def get_latest(self) -> float | None:
        """Jüngster Total-Put/Call-Tageswert. `None`, wenn nicht ermittelbar
        (Feiertag/Quelle weg) — der Aufrufer wertet das als fehlendes Signal."""

    @abstractmethod
    def get_history(self, n_days: int = 90) -> list[float]:
        """Bis zu `n_days` tägliche Total-Put/Call-Werte (jüngste zuerst) für den
        z-Score. Leere Liste, wenn nichts sammelbar (kein Crash, kein Regress)."""
