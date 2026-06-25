from core.domain.taxonomy import Underlying
from core.ports.cost_floor import CostFloorProvider


class StubCostFloorProvider(CostFloorProvider):
    """Platzhalter, bis eine echte Kostenboden-Quelle angebunden ist (Stubs-Initiative).

    Liefert immer None → der Futures-Short deckelt mangels Boden konservativ (kein frischer Short)."""

    async def get_cost_floor(self, underlying: Underlying, symbol: str) -> float | None:
        return None
