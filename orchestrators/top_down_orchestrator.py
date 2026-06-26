import asyncio

from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent_makro import CommodityChiefAgentMakro
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.models import CockpitResult
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, MarketDataProvider, SnbDataProvider, SentimentDataProvider
from core.ports.dated_history import DatedHistoryPort
from core.ports.event_bus import EventBus
from core.ports.world_bank import MarketCapToGdpProvider


class TopDownOrchestrator:
    """
    Modus 1 — Top-Down Analyse.
    Koordiniert 5 ChiefAgents und gibt ein CockpitResult zurück.
    """

    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
        sentiment: SentimentDataProvider | None = None,
        history: DatedHistoryPort | None = None,
        world_bank: MarketCapToGdpProvider | None = None,
    ):
        self.macro_chief       = MacroChiefAgent(macro, ecb, snb, bus, history=history, world_bank=world_bank)
        self.commodity_chief   = CommodityChiefAgentMakro(market, bus)
        self.sentiment_chief   = SentimentChiefAgent(market, bus, sentiment, history=history)
        self.yield_curve_chief = YieldCurveChiefAgent(macro, ecb, snb, bus, history=history)
        self.sector_chief      = SectorChiefAgent(market, bus)

    async def run(self) -> CockpitResult:
        macro, commodities, sentiment, yield_curve = await asyncio.gather(
            self.macro_chief.run(),
            self.commodity_chief.run(),
            self.sentiment_chief.run(),
            self.yield_curve_chief.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        macro       = _safe(macro,       MacroChiefAgent.default())
        commodities = _safe(commodities, CommodityChiefAgentMakro.default())
        sentiment   = _safe(sentiment,   SentimentChiefAgent.default())
        yield_curve = _safe(yield_curve, YieldCurveChiefAgent.default())

        try:
            sectors = await self.sector_chief.run(macro.regime)
        except Exception:
            sectors = SectorChiefAgent.default()

        return CockpitResult(
            macro=macro,
            commodities=commodities,
            sentiment=sentiment,
            yield_curve=yield_curve,
            sectors=sectors,
        )
