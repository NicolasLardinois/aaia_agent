from dataclasses import dataclass
from typing import Optional

from core.domain.models import RiskAffinity


@dataclass(frozen=True)
class Position:
    ticker: str
    shares: float
    entry_price: float          # aus JSON-Key "buy_price"
    direction: str              # "long" | "short" — PFLICHT
    currency: str = "USD"
    current_price: Optional[float] = None
    sector: str = "Unbekannt"
    asset_class: str = "equity"
    country: str = "Unbekannt"
    risk_affinity: Optional[RiskAffinity] = None   # nur Anleihen (konservativ/neutral/risikofreudig)


class PortfolioError(Exception):
    """Ungültige/fehlende Positionsdaten (z. B. fehlende direction)."""
