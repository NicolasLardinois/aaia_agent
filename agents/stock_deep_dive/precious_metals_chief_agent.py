import asyncio

from agents.stock_deep_dive.commodity.cot_agent import COTAgent
from agents.stock_deep_dive.precious_metals.precious_metal_price_agent import PreciousMetalPriceAgent
from agents.stock_deep_dive.precious_metals.cross_metal_agent import CrossMetalAgent
from agents.stock_deep_dive.precious_metals.precious_metals_valuation_agent import PreciousMetalsValuationAgent
from core.domain.events import PreciousMetalsChiefReady
from core.domain.models import PreciousMetalsResult, Signal
from core.ports.data_provider import COTProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus


class PreciousMetalsChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
        cot_provider: COTProvider | None = None,
    ):
        self.bus = bus
        self.pm_price_agent     = PreciousMetalPriceAgent(market, bus, macro=macro)
        self.pm_cross_agent     = CrossMetalAgent(market, bus)
        self.pm_valuation_agent = PreciousMetalsValuationAgent(macro, market, bus)
        # COT (Commitments of Traders): Edelmetalle sind CFTC-berichtspflichtige Futures
        # (GC/SI/PL/PA). Ohne echten Provider (None) liefert der COTAgent UNAVAILABLE →
        # cot_signal bleibt NEUTRAL (wie bisher). Mit CFTC-Adapter wird das konträre
        # Positionierungs-Signal (extreme Managed-Money-Longs → bearish) echt berechnet.
        self.cot_agent          = COTAgent(cot_provider, bus)

    async def run(self, metal: str) -> PreciousMetalsResult:
        results = await asyncio.gather(
            self.pm_price_agent.run(metal),
            self.pm_cross_agent.run(),
            self.pm_valuation_agent.run(metal),
            self.cot_agent.run(metal),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        price_snap     = _safe(results[0], PreciousMetalPriceAgent.default(metal))
        cross_snap     = _safe(results[1], CrossMetalAgent.default())
        valuation_snap = _safe(results[2], PreciousMetalsValuationAgent.default())
        cot_snap       = _safe(results[3], COTAgent.default())

        self.bus.publish(PreciousMetalsChiefReady(source="precious_metals_chief_agent", payload={"metal": metal}))

        return PreciousMetalsResult(
            metal=metal,
            price_analysis=price_snap,
            cross_metal=cross_snap,
            valuation_range=valuation_snap,
            cot_signal=cot_snap.signal,
            currency_impact={},
        )

    @staticmethod
    def default(metal: str = "") -> PreciousMetalsResult:
        return PreciousMetalsResult(
            metal=metal,
            price_analysis=PreciousMetalPriceAgent.default(metal),
            cross_metal=CrossMetalAgent.default(),
            valuation_range=PreciousMetalsValuationAgent.default(),
            cot_signal=Signal.NEUTRAL,
            currency_impact={},
        )
