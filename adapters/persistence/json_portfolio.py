import json
import os

from core.domain.models import PositionState
from core.domain.portfolio import Position, PortfolioError
from core.ports.portfolio_port import PortfolioPort

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")
_VALID_DIR = {"long", "short"}


class JsonPortfolioProvider(PortfolioPort):
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path

    def get_positions(self) -> list[Position]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return []
        out = []
        for d in data.get("positions", []):
            direction = d.get("direction")
            ticker = d.get("ticker", "?")
            if direction not in _VALID_DIR:
                raise PortfolioError(
                    f"Position {ticker}: direction fehlt/ungültig ({direction!r}) — "
                    f"muss 'long' oder 'short' sein.")
            # shares/buy_price sind ebenfalls Pflicht — gleiche Fail-loud-Behandlung
            # wie bei direction, damit Konsumenten EINE klare Fehlerart abfangen können.
            for feld in ("shares", "buy_price"):
                if feld not in d:
                    raise PortfolioError(
                        f"Position {ticker}: Pflichtfeld {feld!r} fehlt — "
                        f"'shares' und 'buy_price' sind erforderlich.")
            out.append(Position(
                ticker=ticker, shares=d["shares"], entry_price=d["buy_price"],
                direction=direction, currency=d.get("currency", "USD"),
                current_price=d.get("current_price"),
                sector=d.get("sector", "Unbekannt"),
                asset_class=d.get("asset_class", "equity"),
                country=d.get("country", "Unbekannt")))
        return out

    def position_state_for(self, ticker: str) -> PositionState:
        # Ticker kanonisch in Großschrift abgleichen — System-Ticker sind upper;
        # toleriert abweichende CLI-/Depot-Schreibweise ('aapl' findet 'AAPL').
        want = ticker.upper()
        for p in self.get_positions():
            if p.ticker.upper() == want:
                return PositionState.LONG if p.direction == "long" else PositionState.SHORT
        return PositionState.NONE
