from abc import ABC, abstractmethod

from core.domain.models import FundInfo


class FundInfoProvider(ABC):
    """Port für ETF-/Fonds-Stammdaten (TER) + Benchmark-Renditen (Tracking-Error)."""

    @abstractmethod
    async def get_fund_info(self, symbol: str) -> FundInfo | None:
        """Liefert die Fund-Info oder None (UNAVAILABLE), wenn keine Daten vorliegen."""
        ...
