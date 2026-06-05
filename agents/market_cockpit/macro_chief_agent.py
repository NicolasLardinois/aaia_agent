import asyncio

from agents.market_cockpit.macro.inflation_agent import InflationAgent
from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from agents.market_cockpit.macro.gdp_agent import GDPAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.macro.buffett_indicator_agent import BuffettIndicatorAgent
from core.domain.events import MacroChiefReady
from core.domain.models import MacroChiefResult, MarketRegime
from core.domain.regime import RegimeDetector
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus


class MacroChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        bus: EventBus,
    ):
        self._macro    = macro
        self._detector = RegimeDetector()
        self.bus       = bus

        self.inflation_agent        = InflationAgent(macro, ecb, snb, bus)
        self.money_supply_agent     = MoneySupplyAgent(macro, ecb, snb, bus)
        self.interest_rate_agent    = InterestRateAgent(macro, ecb, snb, bus)
        self.gdp_agent              = GDPAgent(macro, ecb, snb, bus)
        self.labor_income_agent     = LaborIncomeAgent(macro, bus)
        self.credit_agent           = CreditAgent(macro, bus)
        self.buffett_indicator_agent = BuffettIndicatorAgent(macro, bus)

    async def run(self) -> MacroChiefResult:
        results = await asyncio.gather(
            self.inflation_agent.run(),
            self.money_supply_agent.run(),
            self.interest_rate_agent.run(),
            self.gdp_agent.run(),
            self.labor_income_agent.run(),
            self.credit_agent.run(),
            self.buffett_indicator_agent.run(),
            asyncio.to_thread(self._macro.get_economic_state),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        inflation          = _safe(results[0], InflationAgent.default())
        money_supply       = _safe(results[1], MoneySupplyAgent.default())
        interest_rate      = _safe(results[2], InterestRateAgent.default())
        gdp                = _safe(results[3], GDPAgent.default())
        labor_income       = _safe(results[4], LaborIncomeAgent.default())
        credit             = _safe(results[5], CreditAgent.default())
        buffett_indicator  = _safe(results[6], BuffettIndicatorAgent.default())
        state              = _safe(results[7], {})

        regime, confidence, _ = self._detector.detect(state)

        self.bus.publish(MacroChiefReady(source="macro_chief_agent", payload={
            "regime": regime.value, "confidence": confidence,
        }))

        return MacroChiefResult(
            regime=regime,
            regime_confidence=confidence,
            inflation=inflation,
            money_supply=money_supply,
            interest_rate=interest_rate,
            gdp=gdp,
            labor_income=labor_income,
            credit=credit,
            buffett_indicator=buffett_indicator,
        )

    @staticmethod
    def default() -> MacroChiefResult:
        return MacroChiefResult(
            regime=MarketRegime.EXPANSION,
            regime_confidence=0.5,
            inflation=InflationAgent.default(),
            money_supply=MoneySupplyAgent.default(),
            interest_rate=InterestRateAgent.default(),
            gdp=GDPAgent.default(),
            labor_income=LaborIncomeAgent.default(),
            credit=CreditAgent.default(),
            buffett_indicator=BuffettIndicatorAgent.default(),
        )
