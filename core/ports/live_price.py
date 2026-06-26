"""Port: Live-Kurse + Wechselkurse für den Portfolio-Monitor.

Hexagonal (AGENTS.md §1): der Agent hängt nur von diesem ABC ab, nie von
`yfinance`. Beide Methoden sind **synchron** (blockierendes I/O) — der Agent
wickelt sie bei Bedarf in `asyncio.to_thread(...)`.
"""
from abc import ABC, abstractmethod


class LivePriceProvider(ABC):
    """Liefert den aktuellen Spotkurs eines Tickers und einen Wechselkurs."""

    @abstractmethod
    def get_current_price(self, ticker: str) -> float | None:
        """Aktueller Kurs des Tickers. `None`, wenn nicht ermittelbar (delistet,
        Quelle weg) — der Aufrufer fällt dann defensiv auf den Einstandskurs zurück."""

    @abstractmethod
    def get_fx_rate(self, from_ccy: str, to_ccy: str) -> float:
        """Wechselkurs `from_ccy → to_ccy`. Bei gleicher Währung oder Fehler `1.0`
        (kein stiller Fehlbetrag in der Exposure-Rechnung)."""
