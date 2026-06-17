import asyncio

from core.domain.events import SupplyDemandReady
from core.domain.models import SupplyDemandSnapshot, Signal, SignalStatus
from core.ports.data_provider import CommoditySupplyProvider
from core.ports.event_bus import EventBus

_DEFAULT = SupplyDemandSnapshot(
    inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None,
    production_change_yoy=None, stock_to_flow=None, stock_to_flow_signal=None,
    signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
)

# Einheitliche S2F-Definition: oberirdische Bestände / Jahresproduktion (Jahre).
# Nur dort gesetzt, wo diese Definition belastbar ist (Edelmetalle). Industrie-/Energie-
# Rohstoffe: kein vergleichbarer S2F → None (Lagerreichweite ist dort das relevante Maß).
_STOCK_TO_FLOW: dict[str, float] = {
    "GC=F": 62.0, "SI=F": 22.0,   # Gold/Silber (konsistent mit precious_metal_price)
}

_SCARCE_THRESHOLD = 10.0


def _stf_label(stf: float | None) -> str | None:
    if stf is None:
        return None
    return "scarce" if stf >= _SCARCE_THRESHOLD else "normal"


def _inventory_stats(history: list[dict]) -> tuple[float | None, float | None, float | None]:
    if not history:
        return None, None, None
    vals = [float(h["inventory"]) for h in history if h.get("inventory") is not None]
    if len(vals) < 12:
        return None, None, None
    current = vals[-1]
    avg5 = sum(vals) / len(vals)
    pct = round((current - avg5) / avg5 * 100, 1) if avg5 else None
    return round(current, 1), round(avg5, 1), pct


def _signal(pct_vs_avg: float | None) -> Signal:
    if pct_vs_avg is None:
        return Signal.NEUTRAL
    if pct_vs_avg < -10:
        return Signal.BULLISH
    if pct_vs_avg > 20:
        return Signal.BEARISH
    return Signal.NEUTRAL


class SupplyDemandAgent:
    def __init__(self, supply: CommoditySupplyProvider | None, bus: EventBus):
        self.supply = supply
        self.bus = bus

    async def run(self, ticker: str) -> SupplyDemandSnapshot:
        if self.supply is None:
            self.bus.publish(SupplyDemandReady(source="supply_demand_agent", payload={"ticker": ticker}))
            return _DEFAULT
        history = await asyncio.to_thread(self.supply.get_inventory_history, ticker, 5)
        current, avg5, pct = _inventory_stats(history)
        stf = _STOCK_TO_FLOW.get(ticker)

        if pct is None:
            result = SupplyDemandSnapshot(
                inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None,
                production_change_yoy=None, stock_to_flow=stf, stock_to_flow_signal=_stf_label(stf),
                signal=Signal.NEUTRAL, status=SignalStatus.UNAVAILABLE,
            )
        else:
            result = SupplyDemandSnapshot(
                inventory_current=current, inventory_avg_5y=avg5, inventory_pct_vs_avg=pct,
                production_change_yoy=None, stock_to_flow=stf, stock_to_flow_signal=_stf_label(stf),
                signal=_signal(pct), status=SignalStatus.AVAILABLE,
            )
        self.bus.publish(SupplyDemandReady(source="supply_demand_agent", payload={"ticker": ticker}))
        return result

    @staticmethod
    def default() -> SupplyDemandSnapshot:
        return _DEFAULT
