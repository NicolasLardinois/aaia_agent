import asyncio

from core.domain.events import SectorCompositionReady
from core.domain.models import SectorCompositionSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT = SectorCompositionSnapshot(
    top_sector=None, top_sector_weight=None,
    top_holding=None, top_holding_weight=None,
    top_10_concentration=None, signal=Signal.NEUTRAL,
)

# Hardcoded top sector per major index (approx. 2025)
_TOP_SECTOR: dict[str, tuple[str, float]] = {
    "^GSPC":     ("Technology",        31.0),
    "^NDX":      ("Technology",        60.0),
    "^DJI":      ("Technology",        22.0),
    "^RUT":      ("Financials",        17.0),
    "^STOXX50E": ("Financials",        18.0),
    "^GDAXI":    ("Industrials",       18.0),
    "^FCHI":     ("Luxury/Consumer",   20.0),
    "^SSMI":     ("Healthcare",        40.0),
    "^N225":     ("Technology",        22.0),
    "^HSI":      ("Financials",        35.0),
    "URTH":      ("Technology",        23.0),
    "EEM":       ("Technology",        22.0),
}

# Hardcoded top holding per major index
_TOP_HOLDING: dict[str, tuple[str, float]] = {
    "^GSPC":     ("Apple (AAPL)",   7.0),
    "^NDX":      ("Apple (AAPL)",  12.0),
    "^DJI":      ("Goldman Sachs", 9.0),
    "^STOXX50E": ("ASML",          8.0),
    "^GDAXI":    ("SAP",          14.0),
    "^SSMI":     ("Nestlé",       22.0),
}

# TODO: Echte Holdings über ETF-Anbieter APIs (iShares, SPDR) abrufen


class SectorCompositionAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.market = market
        self.bus    = bus

    async def run(self, ticker: str) -> SectorCompositionSnapshot:
        sector_data  = _TOP_SECTOR.get(ticker)
        holding_data = _TOP_HOLDING.get(ticker)

        result = SectorCompositionSnapshot(
            top_sector=sector_data[0] if sector_data else None,
            top_sector_weight=sector_data[1] if sector_data else None,
            top_holding=holding_data[0] if holding_data else None,
            top_holding_weight=holding_data[1] if holding_data else None,
            top_10_concentration=None,   # TODO: ETF holdings API
            signal=Signal.NEUTRAL,
        )
        self.bus.publish(SectorCompositionReady(source="sector_composition_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SectorCompositionSnapshot:
        return _DEFAULT
