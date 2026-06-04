import asyncio

from core.domain.events import SupplyDemandReady
from core.domain.models import SupplyDemandSnapshot, Signal
from core.ports.event_bus import EventBus

_DEFAULT = SupplyDemandSnapshot(
    inventory_current=None, inventory_avg_5y=None,
    inventory_pct_vs_avg=None, production_change_yoy=None,
    stock_to_flow=None, stock_to_flow_signal=None,
    signal=Signal.NEUTRAL,
)

# Stock-to-Flow: Gesamtbestand / Jahresproduktion (in Jahren)
# Je höher, desto knapper relativ zur Produktion → selteneres Gut
_STOCK_TO_FLOW: dict[str, float] = {
    # Energie — sehr niedrig (wird sofort verbraucht)
    "CL=F":   0.1,   # WTI Öl
    "BZ=F":   0.1,   # Brent
    "NG=F":   0.1,   # Erdgas
    # Industriemetalle
    "HG=F":   0.5,   # Kupfer
    "ALI=F":  0.4,   # Aluminium
    "ZNC=F":  0.4,   # Zink
    "NI=F":   0.5,   # Nickel
    # Agrar (saisonale Lagerbestände, ~3-6 Monate)
    "ZW=F":   0.3,   # Weizen
    "ZC=F":   0.3,   # Mais
    "ZS=F":   0.3,   # Soja
    "KC=F":   0.8,   # Kaffee
    "SB=F":   0.4,   # Zucker
    "CT=F":   0.5,   # Baumwolle
    "OJ=F":   0.3,   # Orangensaft
}

# Interpretation: ab welchem S/F-Wert gilt ein Rohstoff als "scarce"
_SCARCE_THRESHOLD  = 10.0   # > 10 Jahre Bestand → sehr selten (Gold, Silber)
_ABUNDANT_THRESHOLD = 0.5   # < 0.5 Jahre → schnell verbraucht


def _stf_label(stf: float | None) -> str | None:
    if stf is None:
        return None
    if stf >= _SCARCE_THRESHOLD:
        return "scarce"
    if stf <= _ABUNDANT_THRESHOLD:
        return "abundant"
    return "normal"


def _signal(pct_vs_avg: float | None) -> Signal:
    if pct_vs_avg is None:
        return Signal.NEUTRAL
    if pct_vs_avg < -10:
        return Signal.BULLISH   # tiefe Lager → Preisdruck nach oben
    if pct_vs_avg > 20:
        return Signal.BEARISH   # hohe Lager → Preisdruck nach unten
    return Signal.NEUTRAL


# TODO: EIA (Öl/Gas), USDA (Agrar), LME (Metalle) APIs implementieren.


class SupplyDemandAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def run(self, ticker: str) -> SupplyDemandSnapshot:
        stf = _STOCK_TO_FLOW.get(ticker)
        result = SupplyDemandSnapshot(
            inventory_current=None,
            inventory_avg_5y=None,
            inventory_pct_vs_avg=None,
            production_change_yoy=None,
            stock_to_flow=stf,
            stock_to_flow_signal=_stf_label(stf),
            signal=Signal.NEUTRAL,
        )
        self.bus.publish(SupplyDemandReady(source="supply_demand_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SupplyDemandSnapshot:
        return _DEFAULT
