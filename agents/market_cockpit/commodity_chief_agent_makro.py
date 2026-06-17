import asyncio

from agents.market_cockpit.commodity.energy_agent import EnergyAgent
from agents.market_cockpit.commodity.industrial_metals_agent import IndustrialMetalsAgent
from agents.market_cockpit.commodity.precious_metals_macro_agent import PreciousMetalsMacroAgent
from agents.market_cockpit.commodity.agricultural_agent import AgriculturalAgent
from core.domain.events import CommodityChiefReady
from core.domain.models import CommodityChiefResult, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.aggregation import weighted_signal

# Makro-Relevanz-Gewichte (GSCI/BCOM-nah: Energie dominiert)
_WEIGHTS = {"energy": 0.50, "industrial": 0.20, "precious": 0.15, "agricultural": 0.15}


def _aggregate(items):
    return weighted_signal(items)


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

        # Status je Sub-Agent aus dem Vorhandensein der Rohdaten
        status_energy     = (
            SignalStatus.UNAVAILABLE
            if energy.wti_usd is None and energy.brent_usd is None and energy.natural_gas_usd is None
            else SignalStatus.AVAILABLE
        )
        status_industrial = (
            SignalStatus.UNAVAILABLE
            if industrial_metals.copper_usd is None and industrial_metals.aluminium_usd is None
            else SignalStatus.AVAILABLE
        )
        status_precious   = (
            SignalStatus.UNAVAILABLE
            if precious_metals.gold_usd is None and precious_metals.silver_usd is None
            else SignalStatus.AVAILABLE
        )
        status_agri       = (
            SignalStatus.UNAVAILABLE
            if all(
                v is None for v in [
                    agricultural.wheat_usd, agricultural.corn_usd, agricultural.soy_usd,
                    agricultural.coffee_usd, agricultural.sugar_usd,
                    agricultural.cotton_usd, agricultural.orange_juice_usd,
                ]
            )
            else SignalStatus.AVAILABLE
        )

        items = [
            (energy.signal,           _WEIGHTS["energy"],       status_energy),
            (industrial_metals.signal, _WEIGHTS["industrial"], status_industrial),
            (precious_metals.signal,  _WEIGHTS["precious"],    status_precious),
            (agricultural.signal,     _WEIGHTS["agricultural"], status_agri),
        ]
        overall, _conf = _aggregate(items)

        self.bus.publish(CommodityChiefReady(source="commodity_chief_agent", payload={}))

        return CommodityChiefResult(
            energy=energy,
            industrial_metals=industrial_metals,
            precious_metals=precious_metals,
            agricultural=agricultural,
            signal=overall,
        )

    @staticmethod
    def default() -> CommodityChiefResult:
        return CommodityChiefResult(
            energy=EnergyAgent.default(),
            industrial_metals=IndustrialMetalsAgent.default(),
            precious_metals=PreciousMetalsMacroAgent.default(),
            agricultural=AgriculturalAgent.default(),
            signal=Signal.NEUTRAL,
        )
