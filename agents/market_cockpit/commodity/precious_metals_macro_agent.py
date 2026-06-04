import asyncio
from core.domain.events import PreciousMetalsMacroDataReady
from core.domain.models import PreciousMetalsMacroSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

TICKERS = {"gold": "GC=F", "silver": "SI=F", "platinum": "PL=F", "palladium": "PA=F"}
GOLD_SILVER_AVG   = 68.0   # historischer Durchschnitt
GOLD_PLATINUM_AVG = 1.0    # historisch nahe 1:1

_DEFAULT = PreciousMetalsMacroSnapshot(
    gold_usd=None, silver_usd=None, platinum_usd=None, palladium_usd=None,
    gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL,
)


def _signal(gold: float | None, gs_ratio: float | None) -> Signal:
    if gold is None:
        return Signal.NEUTRAL
    # Gold stark steigend = Flucht in Safe Haven → BEARISH für Risikomärkte
    # Gold/Silber-Ratio extrem hoch = Risikoaversion
    if gs_ratio is not None and gs_ratio > 80:
        return Signal.BEARISH
    if gs_ratio is not None and gs_ratio < 50:
        return Signal.BULLISH
    return Signal.NEUTRAL


class PreciousMetalsMacroAgent:
    def __init__(self, provider: MarketDataProvider, bus: EventBus):
        self.provider = provider
        self.bus      = bus

    async def run(self) -> PreciousMetalsMacroSnapshot:
        gold, silver, platinum, palladium = await asyncio.gather(
            asyncio.to_thread(self.provider.get_current_price, TICKERS["gold"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["silver"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["platinum"]),
            asyncio.to_thread(self.provider.get_current_price, TICKERS["palladium"]),
            return_exceptions=True,
        )
        def _safe(v): return None if isinstance(v, Exception) else v
        gold = _safe(gold); silver = _safe(silver)
        platinum = _safe(platinum); palladium = _safe(palladium)

        gs_ratio = round(gold / silver, 2) if gold and silver and silver > 0 else None
        gp_ratio = round(gold / platinum, 2) if gold and platinum and platinum > 0 else None

        result = PreciousMetalsMacroSnapshot(
            gold_usd=gold, silver_usd=silver, platinum_usd=platinum, palladium_usd=palladium,
            gold_silver_ratio=gs_ratio, gold_platinum_ratio=gp_ratio,
            signal=_signal(gold, gs_ratio),
        )
        self.bus.publish(PreciousMetalsMacroDataReady(source="precious_metals_macro_agent", payload={
            "gold": gold, "silver": silver, "gs_ratio": gs_ratio,
        }))
        return result

    @staticmethod
    def default() -> PreciousMetalsMacroSnapshot:
        return _DEFAULT
