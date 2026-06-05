from core.domain.events import SectorRotationDataReady
from core.domain.models import SectorRotationSnapshot, MarketRegime, Signal
from core.ports.event_bus import EventBus

ROTATION_MAP: dict[MarketRegime, dict[str, list[str]]] = {
    MarketRegime.BOOM: {
        "recommended": ["Energy", "Materials", "Industrials"],
        "avoid":       ["Utilities", "ConsumerStap"],
    },
    MarketRegime.EXPANSION: {
        "recommended": ["Technology", "ConsumerDisc", "Financials"],
        "avoid":       ["Utilities"],
    },
    MarketRegime.SLOWDOWN: {
        "recommended": ["Healthcare", "ConsumerStap", "Utilities"],
        "avoid":       ["Energy", "Materials"],
    },
    MarketRegime.RECESSION: {
        "recommended": ["ConsumerStap", "Healthcare", "Utilities"],
        "avoid":       ["Technology", "Financials", "Energy"],
    },
    MarketRegime.RECOVERY: {
        "recommended": ["Financials", "Industrials", "Technology"],
        "avoid":       ["Utilities", "ConsumerStap"],
    },
    MarketRegime.DEPRESSION: {
        "recommended": ["Gold", "ConsumerStap", "Healthcare"],
        "avoid":       ["Technology", "Energy", "Financials", "Industrials"],
    },
}

_DEFAULT = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)


class SectorRotationAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    def run(self, regime: MarketRegime, leading_sector: str) -> SectorRotationSnapshot:
        rotation = ROTATION_MAP.get(regime, {"recommended": [], "avoid": []})
        recommended = rotation["recommended"]
        avoid       = rotation["avoid"]

        if leading_sector in recommended:
            alignment = "aligned"
            signal    = Signal.BULLISH
        elif leading_sector in avoid:
            alignment = "contradicting"
            signal    = Signal.BEARISH
        else:
            alignment = "neutral"
            signal    = Signal.NEUTRAL

        result = SectorRotationSnapshot(
            recommended=recommended, avoid=avoid,
            alignment=alignment, signal=signal,
        )
        self.bus.publish(SectorRotationDataReady(source="sector_rotation_agent", payload={
            "regime": regime.value, "alignment": alignment,
        }))
        return result

    @staticmethod
    def default() -> SectorRotationSnapshot:
        return _DEFAULT
