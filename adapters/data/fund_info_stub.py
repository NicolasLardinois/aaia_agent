from core.domain.models import FundInfo
from core.ports.fund_info import FundInfoProvider


class StubFundInfoProvider(FundInfoProvider):
    """Platzhalter, bis eine echte ETF-Stammdaten-/Benchmark-Quelle angebunden ist.

    Liefert immer None → die Info-Schicht meldet UNAVAILABLE, statt zu raten."""

    async def get_fund_info(self, symbol: str) -> FundInfo | None:
        return None
