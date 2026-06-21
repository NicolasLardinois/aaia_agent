import json
import os

from core.domain.models import PositionState, RiskAffinity
from core.domain.portfolio import Position, PortfolioError
from core.ports.portfolio_port import PortfolioPort

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")
_VALID_DIR = {"long", "short"}
# Aus dem Enum abgeleitet, damit die Whitelist bei einer Erweiterung nicht driftet.
_VALID_AFFINITY = {a.value for a in RiskAffinity}


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
            risk_affinity = d.get("risk_affinity")
            if d.get("asset_class", "equity") == "bond":
                if risk_affinity not in _VALID_AFFINITY:
                    raise PortfolioError(
                        f"Position {ticker}: Anleihe braucht 'risk_affinity' "
                        f"(konservativ|neutral|risikofreudig), war {risk_affinity!r}.")
            out.append(Position(
                ticker=ticker, shares=d["shares"], entry_price=d["buy_price"],
                direction=direction, currency=d.get("currency", "USD"),
                current_price=d.get("current_price"),
                sector=d.get("sector", "Unbekannt"),
                asset_class=d.get("asset_class", "equity"),
                country=d.get("country", "Unbekannt"),
                risk_affinity=risk_affinity))
        return out

    def position_state_for(self, ticker: str) -> PositionState:
        for p in self.get_positions():
            if p.ticker == ticker:
                return PositionState.LONG if p.direction == "long" else PositionState.SHORT
        return PositionState.NONE
