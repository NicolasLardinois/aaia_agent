import asyncio
import logging

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
from agents.stock_deep_dive.equity.quality_agent import QualityAgent
from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent
from agents.stock_deep_dive.equity.insider_agent import InsiderAgent
from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent
from agents.stock_deep_dive.equity.moat_agent import MoatAgent
from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent
from agents.stock_deep_dive.equity.momentum_agent import EquityMomentumAgent
from core.domain.events import EquityChiefReady
from core.domain.models import EquityChiefResult, Signal, SignalStatus
from core.ports.data_provider import FundamentalsProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider
from core.utils.aggregation import weighted_signal
from core.utils.safe import safe_result

_log = logging.getLogger(__name__)

# Gewichte: Bewertung = Langfrist-Anker, Qualität/Moat = Prämien-Rechtfertigung,
# Earnings/Insider/Short/Momentum = Timing/Bestätigung.
# Momentum (0.10) ist sekundär — Preis-Trend bestätigt oder bremst das fundamentale Urteil,
# aber ein einzelnes BEARISH-Momentum-Signal soll NEUTRAL-Bausteine nicht allein überstimmen.
# Summe: 0.25+0.20+0.20+0.15+0.10+0.05+0.05+0.10 = 1.10 → weighted_signal renormalisiert.
_W_VALUATION = 0.25
_W_FUNDAMENTALS = 0.20
_W_QUALITY = 0.20
_W_MOAT = 0.15
_W_EARNINGS = 0.10
_W_INSIDER = 0.05
_W_SHORT = 0.05
_W_MOMENTUM = 0.10


def _status(sig: Signal) -> SignalStatus:
    """NEUTRAL gilt als verfügbar (eine bewusste neutrale Aussage), aber neutrale
    Default-Snapshots tragen ohnehin Gewicht 0-Wirkung im Voting. Hier: alle
    vorhandenen Sub-Signale sind AVAILABLE; UNAVAILABLE bleibt späteren Stubs
    vorbehalten (Plan 0 P1.4)."""
    return SignalStatus.AVAILABLE


def _aggregate_signal(fundamentals_sig, quality_sig, valuation_sig, moat_sig,
                      earnings_sig, insider_sig, short_sig,
                      momentum_sig) -> tuple[Signal, float]:
    items = [
        (valuation_sig,    _W_VALUATION,    _status(valuation_sig)),
        (fundamentals_sig, _W_FUNDAMENTALS, _status(fundamentals_sig)),
        (quality_sig,      _W_QUALITY,      _status(quality_sig)),
        (moat_sig,         _W_MOAT,         _status(moat_sig)),
        (earnings_sig,     _W_EARNINGS,     _status(earnings_sig)),
        (insider_sig,      _W_INSIDER,      _status(insider_sig)),
        (short_sig,        _W_SHORT,        _status(short_sig)),
        (momentum_sig,     _W_MOMENTUM,     _status(momentum_sig)),
    ]
    return weighted_signal(items)


class EquityChiefAgent:
    def __init__(
        self,
        fundamentals: FundamentalsProvider,
        market: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.fundamentals_agent    = FundamentalsAgent(fundamentals, bus)
        self.quality_agent         = QualityAgent(fundamentals, bus)
        self.short_agent           = ShortInterestAgent(fundamentals, bus)
        self.insider_agent         = InsiderAgent(fundamentals, bus)
        self.earnings_agent        = EarningsTrendAgent(fundamentals, bus)
        self.moat_agent            = MoatAgent(llm, bus)
        self.valuation_range_agent = ValuationRangeAgent(fundamentals, market, bus)
        self.momentum_agent        = EquityMomentumAgent(market, bus)

    async def run(self, ticker: str, sector: str = "default") -> EquityChiefResult:
        results = await asyncio.gather(
            self.fundamentals_agent.run(ticker, sector=sector),    # results[0]
            self.quality_agent.run(ticker, sector=sector),         # results[1]
            self.short_agent.run(ticker),                          # results[2]
            self.insider_agent.run(ticker),                        # results[3]
            self.earnings_agent.run(ticker),                       # results[4]
            self.moat_agent.run(ticker),                           # results[5]
            self.valuation_range_agent.run(ticker, sector),        # results[6]
            self.momentum_agent.run(ticker),                       # results[7]
            return_exceptions=True,
        )

        fundamentals    = safe_result(results[0], default=FundamentalsAgent.default(), label="EquityChief: FundamentalsAgent", logger=_log)
        quality         = safe_result(results[1], default=QualityAgent.default(), label="EquityChief: QualityAgent", logger=_log)
        short_interest  = safe_result(results[2], default=ShortInterestAgent.default(), label="EquityChief: ShortInterestAgent", logger=_log)
        insider         = safe_result(results[3], default=InsiderAgent.default(), label="EquityChief: InsiderAgent", logger=_log)
        earnings_trend  = safe_result(results[4], default=EarningsTrendAgent.default(), label="EquityChief: EarningsTrendAgent", logger=_log)
        moat            = safe_result(results[5], default=MoatAgent.default(), label="EquityChief: MoatAgent", logger=_log)
        valuation_range = safe_result(results[6], default=ValuationRangeAgent.default(), label="EquityChief: ValuationRangeAgent", logger=_log)
        momentum        = safe_result(results[7], default=EquityMomentumAgent.default(), label="EquityChief: EquityMomentumAgent", logger=_log)

        overall_signal, confidence = _aggregate_signal(
            fundamentals_sig=fundamentals.signal,
            quality_sig=quality.signal,
            valuation_sig=valuation_range.signal,
            moat_sig=moat.signal,
            earnings_sig=earnings_trend.signal,
            insider_sig=insider.signal,
            short_sig=short_interest.signal,
            momentum_sig=momentum.signal,
        )

        self.bus.publish(EquityChiefReady(source="equity_chief_agent", payload={
            "ticker": ticker, "signal": overall_signal.value, "confidence": round(confidence, 3),
        }))

        return EquityChiefResult(
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=valuation_range,
            momentum=momentum,
        )

    @staticmethod
    def default() -> EquityChiefResult:
        return EquityChiefResult(
            fundamentals=FundamentalsAgent.default(),
            quality=QualityAgent.default(),
            short_interest=ShortInterestAgent.default(),
            insider=InsiderAgent.default(),
            earnings_trend=EarningsTrendAgent.default(),
            moat=MoatAgent.default(),
            valuation_range=ValuationRangeAgent.default(),
        )
