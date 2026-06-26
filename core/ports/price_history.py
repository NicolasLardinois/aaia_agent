"""Port: historische Kursquelle für die Backtester (Forward-Window-Bewertung).

Hexagonal (AGENTS.md §1): die Backtester-Agenten hängen nur von diesem ABC bzw.
einer Kurs-Lookup-Funktion ab, nie von `yfinance`. Die Methode ist **synchron**
(blockierendes I/O) — die Aufrufer wickeln sie bei Bedarf in `to_thread`/laufen
ohnehin in einem eigenen Backtester-Lauf.
"""
from abc import ABC, abstractmethod
from datetime import datetime


class PriceHistoryProvider(ABC):
    """Liefert den ersten Schlusskurs am/nach ``entry_date + horizon_days``."""

    @abstractmethod
    def get_price_on_horizon(
        self, ticker: str, entry_date: datetime, horizon_days: int
    ) -> float | None:
        """Erster Schlusskurs am/nach dem Horizont. `None`, wenn kein Kurs
        ermittelbar (delistet/Quelle weg) — der Aufrufer wertet das defensiv aus."""
