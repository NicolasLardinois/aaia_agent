from abc import ABC, abstractmethod

from core.domain.models import FuturesCurveSnapshot


class FuturesCurveProvider(ABC):
    """Port für Terminkurvendaten (Front-/Folgekontrakt, Verfall, Margin)."""

    @abstractmethod
    async def get_curve(self, symbol: str) -> FuturesCurveSnapshot | None:
        """Liefert die Kurve oder None (UNAVAILABLE), wenn keine Daten vorliegen."""
        ...
