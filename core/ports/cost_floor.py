from abc import ABC, abstractmethod

from core.domain.taxonomy import Underlying


class CostFloorProvider(ABC):
    """Port für den Produktionskosten-Boden (Mean-Reversion-Stütze unter dem Preis)."""

    @abstractmethod
    async def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None:
        """Kostenboden als Preis. Rohstoff: Grenzproduktionskosten; Edelmetall: AISC der Minen.
        None (UNAVAILABLE), wenn keine Daten vorliegen."""
        ...
