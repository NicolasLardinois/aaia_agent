from core.domain.models import FuturesCurveSnapshot
from core.ports.futures_curve import FuturesCurveProvider


class StubFuturesCurveProvider(FuturesCurveProvider):
    """Platzhalter, bis eine echte Terminkurven-Quelle angebunden ist (Stubs-Initiative).

    Liefert immer None → die Mechanik-Schicht meldet UNAVAILABLE, statt zu raten."""

    async def get_curve(self, symbol: str) -> FuturesCurveSnapshot | None:
        return None
