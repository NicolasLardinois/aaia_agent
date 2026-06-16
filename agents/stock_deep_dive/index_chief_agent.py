import asyncio

from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent
from agents.stock_deep_dive.index.index_valuation_agent import IndexValuationAgent
from agents.stock_deep_dive.index.index_earnings_agent import IndexEarningsAgent
from agents.stock_deep_dive.index.index_breadth_agent import IndexBreadthAgent
from agents.stock_deep_dive.index.index_momentum_agent import IndexMomentumAgent
from agents.stock_deep_dive.index.sector_composition_agent import SectorCompositionAgent
from agents.stock_deep_dive.index.index_valuation_range_agent import IndexValuationRangeAgent
from core.domain.events import IndexChiefReady
from core.domain.models import IndexResult, Signal, SignalStatus
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.aggregation import weighted_signal

# Top-down-Gewichte: Bewertung = Langfrist-Anker, Momentum/Breadth = Timing.
_W_VALUATION = 0.30
_W_MOMENTUM  = 0.25
_W_BREADTH   = 0.20
_W_EARNINGS  = 0.15
_W_PRICE     = 0.10


def _aggregate_index_signal(valuation_sig, momentum_sig, earnings_sig,
                            breadth_sig, price_sig) -> tuple[Signal, float]:
    A = SignalStatus.AVAILABLE
    items = [
        (valuation_sig, _W_VALUATION, A),
        (momentum_sig,  _W_MOMENTUM,  A),
        (breadth_sig,   _W_BREADTH,   A),
        (earnings_sig,  _W_EARNINGS,  A),
        (price_sig,     _W_PRICE,     A),
    ]
    return weighted_signal(items)


class IndexChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.index_price_agent           = IndexPriceAgent(market, bus)
        self.index_valuation_agent       = IndexValuationAgent(market, bus)
        self.index_earnings_agent        = IndexEarningsAgent(market, bus)
        self.index_breadth_agent         = IndexBreadthAgent(market, bus)
        self.index_momentum_agent        = IndexMomentumAgent(market, bus)
        self.sector_composition_agent    = SectorCompositionAgent(market, bus)
        self.index_valuation_range_agent = IndexValuationRangeAgent(market, bus)

    async def run(self, ticker: str) -> IndexResult:
        results = await asyncio.gather(
            self.index_price_agent.run(ticker),
            self.index_valuation_agent.run(ticker),
            self.index_earnings_agent.run(ticker),
            self.index_breadth_agent.run(ticker),
            self.index_momentum_agent.run(ticker),
            self.sector_composition_agent.run(ticker),
            self.index_valuation_range_agent.run(ticker),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        price           = _safe(results[0], IndexPriceAgent.default())
        valuation       = _safe(results[1], IndexValuationAgent.default())
        earnings        = _safe(results[2], IndexEarningsAgent.default())
        breadth         = _safe(results[3], IndexBreadthAgent.default())
        momentum        = _safe(results[4], IndexMomentumAgent.default())
        composition     = _safe(results[5], SectorCompositionAgent.default())
        valuation_range = _safe(results[6], IndexValuationRangeAgent.default())

        overall_signal, confidence = _aggregate_index_signal(
            valuation_sig=valuation.signal,
            momentum_sig=momentum.signal,
            earnings_sig=earnings.signal,
            breadth_sig=breadth.signal,
            price_sig=price.signal,
        )

        self.bus.publish(IndexChiefReady(source="index_chief_agent", payload={
            "ticker": ticker, "signal": overall_signal.value, "confidence": round(confidence, 3),
        }))

        return IndexResult(
            ticker=ticker, price=price, valuation=valuation, earnings=earnings,
            breadth=breadth, momentum=momentum, composition=composition,
            valuation_range=valuation_range,
        )

    @staticmethod
    def default(ticker: str = "") -> IndexResult:
        return IndexResult(
            ticker=ticker,
            price=IndexPriceAgent.default(),
            valuation=IndexValuationAgent.default(),
            earnings=IndexEarningsAgent.default(),
            breadth=IndexBreadthAgent.default(),
            momentum=IndexMomentumAgent.default(),
            composition=SectorCompositionAgent.default(),
            valuation_range=IndexValuationRangeAgent.default(),
        )
