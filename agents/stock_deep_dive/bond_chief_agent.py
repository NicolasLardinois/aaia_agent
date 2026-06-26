import asyncio

from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from agents.stock_deep_dive.bond.bond_credit_agent import BondCreditAgent
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent
from core.domain.events import BondChiefReady
from core.domain.models import BondResult, Signal, RiskAffinity, CreditBand, SignalStatus
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
from core.ports.event_bus import EventBus
from core.utils.bond_risk import rating_to_band, aggregate_bond_signal
from core.utils.safe import safe_result


class BondChiefAgent:
    def __init__(
        self,
        fundamentals: FundamentalsProvider,
        macro: MacroDataProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.bond_metrics_agent  = BondMetricsAgent(fundamentals, macro, bus)
        self.bond_duration_agent = BondDurationAgent(fundamentals, bus)
        self.bond_credit_agent   = BondCreditAgent(fundamentals, bus)
        self.bond_spread_agent   = BondSpreadAgent(fundamentals, bus)

    async def run(self, ticker: str, bond_type: str, rate_direction: str,
                  risk_affinity: RiskAffinity) -> BondResult:
        """Aggregiert alle Bond-Sub-Agenten und berechnet das Gesamtsignal via Risikoaffinität.

        Das frühere Credit-Veto (_overall_signal) entfällt bewusst: stattdessen fliesst das
        Credit-Band als gewichteter Beitrag in aggregate_bond_signal ein — Höhe abhängig von
        der Risikoaffinität des Investors (konservativ/neutral/risikofreudig).
        """
        results = await asyncio.gather(
            self.bond_metrics_agent.run(ticker, bond_type),
            self.bond_duration_agent.run(ticker, rate_direction),
            self.bond_credit_agent.run(ticker),
            self.bond_spread_agent.run(ticker),
            return_exceptions=True,
        )

        metrics  = safe_result(results[0], default=BondMetricsAgent.default())
        duration = safe_result(results[1], default=BondDurationAgent.default())
        credit   = safe_result(results[2], default=BondCreditAgent.default())
        spread   = safe_result(results[3], default=BondSpreadAgent.default())

        # §3.4: Eine Komponente ohne verfügbare Daten (UNAVAILABLE) wird als None
        # weitergereicht → aggregate_bond_signal lässt sie weg und re-normalisiert,
        # statt sie als neutrale 0-Stimme mitzuzählen.
        def _avail(snap): return snap.signal if snap.status == SignalStatus.AVAILABLE else None

        credit_band = rating_to_band(credit.sp)
        overall, confidence = aggregate_bond_signal(
            _avail(metrics), _avail(duration), _avail(spread), credit_band, risk_affinity,
        )
        self.bus.publish(BondChiefReady(source="bond_chief_agent", payload={
            "ticker": ticker, "overall_signal": overall.value,
            "duration": duration.modified_duration,
            "default_probability": credit.default_probability,
        }))
        return BondResult(
            ticker=ticker, bond_type=bond_type,
            metrics=metrics, duration=duration, credit=credit, spread=spread,
            overall_signal=overall, confidence=confidence,
            risk_affinity=risk_affinity, credit_band=credit_band,
        )

    @staticmethod
    def default(ticker: str = "", bond_type: str = "government") -> BondResult:
        return BondResult(
            ticker=ticker, bond_type=bond_type,
            metrics=BondMetricsAgent.default(),
            duration=BondDurationAgent.default(),
            credit=BondCreditAgent.default(),
            spread=BondSpreadAgent.default(),
        )
