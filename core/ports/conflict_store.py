from abc import ABC, abstractmethod

from core.domain.models import ConflictItem


class ConflictStorePort(ABC):
    """Port (abstrakte Schnittstelle) für die Konflikt-Persistenz.

    Adapter (z. B. Supabase, In-Memory) implementieren diese Klasse.
    Agenten und Domänen-Logik hängen ausschließlich von diesem Port ab —
    niemals direkt von einem konkreten Adapter (Hexagonal-Regel).
    """

    @abstractmethod
    def find_open(self, ticker: str, direction: str) -> ConflictItem | None:
        """Gibt den ersten offenen (status='open') Konflikt für ticker+direction zurück."""
        ...

    @abstractmethod
    def find_latest_resolved(self, ticker: str, direction: str) -> ConflictItem | None:
        """Gibt den neusten erledigten (status='resolved') Konflikt für ticker+direction zurück."""
        ...

    @abstractmethod
    def save(self, item: ConflictItem) -> None:
        """Persistiert einen neuen oder aktualisierten ConflictItem."""
        ...

    @abstractmethod
    def load_open(self) -> list[ConflictItem]:
        """Lädt alle offenen Konflikte (für proaktive Inbox-Anzeige)."""
        ...

    @abstractmethod
    def resolve(self, conflict_id: int, user_decision: str) -> None:
        """Markiert einen Konflikt als erledigt und speichert die Nutzer-Entscheidung."""
        ...
