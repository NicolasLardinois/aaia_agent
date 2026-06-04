import concurrent.futures

from agents.market_cockpit.macro_regime_agent import MacroRegimeAgent
from agents.market_cockpit.commodity_agent import CommodityAgent
from agents.market_cockpit.sentiment_agent import SentimentAgent
from agents.market_cockpit.yield_curve_agent import YieldCurveAgent
from agents.market_cockpit.sector_agent import SectorAgent
from core.domain.models import CockpitResult
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus


class CockpitOrchestrator:
    """Führt alle Modus-1-Agenten parallel aus und gibt CockpitResult zurück."""

    def __init__(
        self,
        macro_provider: MacroDataProvider,
        market_provider: MarketDataProvider,
        bus: EventBus,
    ):
        self.macro_agent    = MacroRegimeAgent(macro_provider, bus)
        self.commodity_agent = CommodityAgent(market_provider, bus)
        self.sentiment_agent = SentimentAgent(market_provider, bus)
        self.yield_agent    = YieldCurveAgent(macro_provider, bus)
        self.sector_agent   = SectorAgent(market_provider, bus)

    def run(self) -> CockpitResult:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            f_macro     = executor.submit(self.macro_agent.run)
            f_commodity = executor.submit(self.commodity_agent.run)
            f_sentiment = executor.submit(self.sentiment_agent.run)
            f_yield     = executor.submit(self.yield_agent.run)
            f_sector    = executor.submit(self.sector_agent.run)

        return CockpitResult(
            macro=f_macro.result(),
            commodities=f_commodity.result(),
            sentiment=f_sentiment.result(),
            yield_curve=f_yield.result(),
            sectors=f_sector.result(),
        )
