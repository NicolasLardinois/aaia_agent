from dataclasses import dataclass
from typing import Optional

from core.domain.models import RiskAffinity
from core.domain.taxonomy import Underlying, Wrapper, legacy_asset_class


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
    # Ablösung von asset_class: str — Abwärtskompatibilität via Property unten.
    underlying: Underlying = Underlying.EQUITY
    wrapper: Wrapper = Wrapper.SINGLE
    country: str = "Unbekannt"
    risk_affinity: Optional[RiskAffinity] = None   # nur Anleihen (konservativ/neutral/risikofreudig)

    @property
    def asset_class(self) -> str:
        """Übergangs-Property: liefert den Alt-String für Code, der noch asset_class liest
        (portfolio_monitor_agent, Tests). Wird in Phase 2 durch direkte underlying/wrapper-Nutzung
        abgelöst. Delegiert an legacy_asset_class() in core/domain/taxonomy.py."""
        return legacy_asset_class(self.underlying, self.wrapper)


class PortfolioError(Exception):
    """Ungültige/fehlende Positionsdaten (z. B. fehlende direction)."""
