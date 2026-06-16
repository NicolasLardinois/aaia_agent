import asyncio
from core.domain.events import BondSpreadReady
from core.domain.models import BondSpreadSnapshot, Signal
from core.ports.data_provider import FundamentalsProvider
from core.ports.event_bus import EventBus

_DEFAULT = BondSpreadSnapshot(
    spread_bps=None, oas=None, z_spread=None, spread_trend="stable",
    signal=Signal.NEUTRAL,
)


def _level_score(spread_bps: float | None, history: list[float] | None) -> str | None:
    """Niveau-Bewertung gegen historisches Mittel (Carry/Value).

    'cheap' = Spread > Mittel + 0.5σ (attraktive Risikoprämie),
    'rich'  = Spread < Mittel − 0.5σ, sonst 'fair'.
    """
    if spread_bps is None or not history:
        return None
    mean = sum(history) / len(history)
    var = sum((h - mean) ** 2 for h in history) / len(history)
    sd = var ** 0.5
    if sd == 0:
        return "fair"
    z = (spread_bps - mean) / sd
    if z > 0.5:
        return "cheap"
    if z < -0.5:
        return "rich"
    return "fair"


def _signal(spread_bps: float | None, trend: str, level: str | None) -> Signal:
    if spread_bps is None:
        return Signal.NEUTRAL
    if trend == "tightening":
        return Signal.BULLISH
    if trend == "widening":
        return Signal.BEARISH
    # bei stabilem Trend: Value-Komponente als schwaches Signal
    if level == "cheap":
        return Signal.BULLISH
    if level == "rich":
        return Signal.BEARISH
    return Signal.NEUTRAL


class BondSpreadAgent:
    def __init__(self, provider: FundamentalsProvider, bus: EventBus):
        self.provider = provider
        self.bus = bus

    async def run(self, ticker: str) -> BondSpreadSnapshot:
        data = await asyncio.to_thread(self.provider.get_bond_data, ticker)
        if isinstance(data, Exception):
            data = {}

        spread_bps = data.get("spread_bps")
        z_spread = data.get("z_spread")
        oas = data.get("oas")
        # Plausibilität: OAS darf den Z-Spread nicht übersteigen (Optionswert ≥ 0)
        if oas is not None and z_spread is not None and oas > z_spread:
            oas = z_spread
        trend = data.get("spread_trend", "stable")
        history = data.get("spread_history")
        spread_duration = data.get("spread_duration")
        level = _level_score(spread_bps, history)

        result = BondSpreadSnapshot(
            spread_bps=spread_bps, oas=oas, z_spread=z_spread,
            spread_trend=trend, signal=_signal(spread_bps, trend, level),
        )
        self.bus.publish(BondSpreadReady(source="bond_spread_agent", payload={
            "ticker": ticker, "spread_bps": spread_bps, "trend": trend,
            "level": level, "spread_duration": spread_duration,
        }))
        return result

    @staticmethod
    def default() -> BondSpreadSnapshot:
        return _DEFAULT
