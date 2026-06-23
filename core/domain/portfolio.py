from dataclasses import dataclass
from typing import Optional

from core.domain.models import RiskAffinity
from core.domain.taxonomy import Underlying, Wrapper


@dataclass(frozen=True)
class Position:
    ticker: str
    shares: float
    entry_price: float          # aus JSON-Key "buy_price"
    direction: str              # "long" | "short" — PFLICHT
    currency: str = "USD"
    current_price: Optional[float] = None
    sector: str = "Unbekannt"
    # Taxonomie-Achsen (Task 6): underlying = Basiswert-Engine, wrapper = Hüllen-Mechanik.
    underlying: Underlying = Underlying.EQUITY
    wrapper: Wrapper = Wrapper.SINGLE
    country: str = "Unbekannt"
    risk_affinity: Optional[RiskAffinity] = None   # nur Anleihen (konservativ/neutral/risikofreudig)
    contract_multiplier: float = 1.0   # Future: Kontraktgröße fürs Notional; sonst 1.0


class PortfolioError(Exception):
    """Ungültige/fehlende Positionsdaten (z. B. fehlende direction)."""
