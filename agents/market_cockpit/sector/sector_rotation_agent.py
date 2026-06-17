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
        "recommended": ["ConsumerStap", "Healthcare", "Utilities"],
        "avoid":       ["Technology", "Energy", "Financials", "Industrials"],
    },
}


def _alignment(top_sectors: list[str], recommended: list[str], avoid: list[str]) -> tuple[str, Signal]:
    """Top-N-Alignment: Anzahl Empfehlungen vs. Vermeidungs-Treffer in den Top-Sektoren."""
    rec_hits   = sum(1 for s in top_sectors if s in recommended)
    avoid_hits = sum(1 for s in top_sectors if s in avoid)
    if rec_hits >= 2 and rec_hits >= avoid_hits:
        return "aligned", Signal.BULLISH
    if avoid_hits >= 2 and avoid_hits > rec_hits:
        return "contradicting", Signal.BEARISH
    return "neutral", Signal.NEUTRAL

_DEFAULT = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)


class SectorRotationAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus

    def run(self, regime: MarketRegime, top_sectors: list[str]) -> SectorRotationSnapshot:
        rotation    = ROTATION_MAP.get(regime, {"recommended": [], "avoid": []})
        recommended = rotation["recommended"]
        avoid       = rotation["avoid"]

        alignment, signal = _alignment(top_sectors, recommended, avoid)

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
