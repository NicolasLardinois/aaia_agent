import json
import os

from core.domain.models import PositionState, RiskAffinity
from core.domain.portfolio import Position, PortfolioError
from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy
from core.ports.portfolio_port import PortfolioPort

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "portfolio.json")
_VALID_DIR = {"long", "short"}
# Aus dem Enum abgeleitet, damit die Whitelist bei einer Erweiterung nicht driftet.
_VALID_AFFINITY = {a.value for a in RiskAffinity}
# Zulässige Enum-Werte — aus Enum abgeleitet (kein Driften bei Erweiterungen).
_VALID_UNDERLYING = {u.value for u in Underlying}
_VALID_WRAPPER    = {w.value for w in Wrapper}


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
            # --- underlying / wrapper auflösen (Priorität: neu > legacy > Default) --------
            # (1) Neues Schema: underlying + wrapper direkt im JSON → fail-loud bei unbekannt.
            # (2) Legacy-Schlüssel asset_class → legacy_to_taxonomy() (Spec §5).
            # (3) Keiner vorhanden → Domänen-Defaults (Underlying.EQUITY / Wrapper.SINGLE).
            raw_und = d.get("underlying")
            raw_wrap = d.get("wrapper")
            raw_ac  = d.get("asset_class")
            if raw_und is not None or raw_wrap is not None:
                # Neues Schema: beide Achsen müssen gültig sein.
                if raw_und not in _VALID_UNDERLYING:
                    raise PortfolioError(
                        f"Position {ticker}: 'underlying' ungültig ({raw_und!r}) — "
                        f"erlaubt: {sorted(_VALID_UNDERLYING)}.")
                if raw_wrap not in _VALID_WRAPPER:
                    raise PortfolioError(
                        f"Position {ticker}: 'wrapper' ungültig ({raw_wrap!r}) — "
                        f"erlaubt: {sorted(_VALID_WRAPPER)}.")
                underlying = Underlying(raw_und)
                wrapper    = Wrapper(raw_wrap)
            elif raw_ac is not None:
                # Legacy-Schlüssel → Mapping via taxonomy (defensiv: Unbekanntes → equity/single).
                underlying, wrapper = legacy_to_taxonomy(raw_ac)
            else:
                # Kein Klassenhinweis → Domänen-Defaults.
                underlying = Underlying.EQUITY
                wrapper    = Wrapper.SINGLE

            # --- risk_affinity — Anleihen brauchen den Wert (Spec §4.1) ------------------
            risk_affinity = d.get("risk_affinity")
            if underlying is Underlying.BOND:
                if risk_affinity not in _VALID_AFFINITY:
                    raise PortfolioError(
                        f"Position {ticker}: Anleihe braucht 'risk_affinity' "
                        f"(konservativ|neutral|risikofreudig), war {risk_affinity!r}.")
            # In die Domäne als Enum (Typsicherheit, Spec §4.1); ungültig/fehlend → None.
            affinity = RiskAffinity(risk_affinity) if risk_affinity in _VALID_AFFINITY else None
            out.append(Position(
                ticker=ticker, shares=d["shares"], entry_price=d["buy_price"],
                direction=direction, currency=d.get("currency", "USD"),
                current_price=d.get("current_price"),
                sector=d.get("sector", "Unbekannt"),
                underlying=underlying, wrapper=wrapper,
                country=d.get("country", "Unbekannt"),
                risk_affinity=affinity,
                contract_multiplier=float(d.get("contract_multiplier", 1.0))))
        return out

    def position_state_for(self, ticker: str) -> PositionState:
        # Ticker kanonisch in Großschrift abgleichen — System-Ticker sind upper;
        # toleriert abweichende CLI-/Depot-Schreibweise ('aapl' findet 'AAPL').
        want = ticker.upper()
        for p in self.get_positions():
            if p.ticker.upper() == want:
                return PositionState.LONG if p.direction == "long" else PositionState.SHORT
        return PositionState.NONE
