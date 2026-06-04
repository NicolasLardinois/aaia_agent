import asyncio

from agents.stock_deep_dive.commodity.supply_demand_agent import SupplyDemandAgent
from agents.stock_deep_dive.commodity.seasonality_agent import SeasonalityAgent
from agents.stock_deep_dive.commodity.cot_agent import COTAgent
from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import CommodityValuationRangeAgent
from core.domain.events import CommodityBottomUpChiefReady
from core.domain.models import CommodityBottomUpResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class CommodityChiefAgentMikro:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.supply_demand_agent             = SupplyDemandAgent(bus)
        self.seasonality_agent               = SeasonalityAgent(market, bus)
        self.cot_agent                       = COTAgent(bus)
        self.commodity_valuation_range_agent = CommodityValuationRangeAgent(market, bus)

    async def run(self, ticker: str) -> CommodityBottomUpResult:
        results = await asyncio.gather(
            self.supply_demand_agent.run(ticker),
            self.seasonality_agent.run(ticker),
            self.cot_agent.run(ticker),
            self.commodity_valuation_range_agent.run(ticker),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        supply_demand   = _safe(results[0], SupplyDemandAgent.default())
        seasonality     = _safe(results[1], SeasonalityAgent.default())
        cot             = _safe(results[2], COTAgent.default())
        valuation_range = _safe(results[3], CommodityValuationRangeAgent.default())

        self.bus.publish(CommodityBottomUpChiefReady(source="commodity_chief_agent", payload={"ticker": ticker}))

        return CommodityBottomUpResult(
            commodity=ticker,
            supply_demand=supply_demand,
            seasonality=seasonality,
            cot=cot,
            valuation_range=valuation_range,
        )

    @staticmethod
    def default(ticker: str = "") -> CommodityBottomUpResult:
        return CommodityBottomUpResult(
            commodity=ticker,
            supply_demand=SupplyDemandAgent.default(),
            seasonality=SeasonalityAgent.default(),
            cot=COTAgent.default(),
            valuation_range=CommodityValuationRangeAgent.default(),
        )
