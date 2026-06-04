import asyncio

from agents.market_cockpit.commodity.energy_agent import EnergyAgent
from agents.market_cockpit.commodity.industrial_metals_agent import IndustrialMetalsAgent
from agents.market_cockpit.commodity.precious_metals_macro_agent import PreciousMetalsMacroAgent
from agents.market_cockpit.commodity.agricultural_agent import AgriculturalAgent
from core.domain.events import CommodityChiefReady
from core.domain.models import CommodityChiefResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class CommodityChiefAgentMakro:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.energy_agent          = EnergyAgent(market, bus)
        self.industrial_agent      = IndustrialMetalsAgent(market, bus)
        self.precious_metals_agent = PreciousMetalsMacroAgent(market, bus)
        self.agricultural_agent    = AgriculturalAgent(market, bus)

    async def run(self) -> CommodityChiefResult:
        results = await asyncio.gather(
            self.energy_agent.run(),
            self.industrial_agent.run(),
            self.precious_metals_agent.run(),
            self.agricultural_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        energy            = _safe(results[0], EnergyAgent.default())
        industrial_metals = _safe(results[1], IndustrialMetalsAgent.default())
        precious_metals   = _safe(results[2], PreciousMetalsMacroAgent.default())
        agricultural      = _safe(results[3], AgriculturalAgent.default())

        self.bus.publish(CommodityChiefReady(source="commodity_chief_agent", payload={}))

        return CommodityChiefResult(
            energy=energy,
            industrial_metals=industrial_metals,
            precious_metals=precious_metals,
            agricultural=agricultural,
        )

    @staticmethod
    def default() -> CommodityChiefResult:
        return CommodityChiefResult(
            energy=EnergyAgent.default(),
            industrial_metals=IndustrialMetalsAgent.default(),
            precious_metals=PreciousMetalsMacroAgent.default(),
            agricultural=AgriculturalAgent.default(),
        )
