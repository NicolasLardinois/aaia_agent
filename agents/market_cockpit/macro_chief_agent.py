import asyncio

from agents.market_cockpit.macro.inflation_agent import InflationAgent
from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from agents.market_cockpit.macro.gdp_agent import GDPAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from agents.market_cockpit.macro.buffett_indicator_agent import BuffettIndicatorAgent
from core.domain.events import MacroChiefReady
from core.domain.models import MacroChiefResult, MarketRegime, SignalStatus
from core.domain.regime import RegimeDetector
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, SnbDataProvider
from core.ports.dated_history import DatedHistoryPort
from core.ports.event_bus import EventBus


class MacroChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        bus: EventBus,
        history: DatedHistoryPort | None = None,
    ):
        self._macro    = macro
        self._ecb      = ecb
        self._snb      = snb
        self._detector = RegimeDetector()
        self.bus       = bus

        self.inflation_agent        = InflationAgent(macro, ecb, snb, bus)
        self.money_supply_agent     = MoneySupplyAgent(macro, ecb, snb, bus, history=history)
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
            asyncio.to_thread(self._macro.get_yield_spreads),
            asyncio.to_thread(self._ecb.get_yield_spreads),
            asyncio.to_thread(self._snb.get_yield_spreads),
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
        usa_spreads        = _safe(results[8], {}) or {}
        eu_spreads         = _safe(results[9], {}) or {}
        ch_spreads         = _safe(results[10], {}) or {}

        from core.domain.regime_inputs import assemble_regime_inputs

        state, sub_signals = assemble_regime_inputs(
            economic_state=state,
            usa_10y3m=usa_spreads.get("10y3m"),
            eu_spreads=eu_spreads,
            ch_spreads=ch_spreads,
            sub_signal_map={
                "money_supply": money_supply.usa.signal,
                "credit":       credit.usa.signal,
                "labor":        labor_income.usa.signal,
                "buffett":      buffett_indicator.signal,
            },
        )

        regime, confidence, _ = self._detector.detect(state, sub_signals=sub_signals)

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
        # Bug #30: Fällt der ganze Macro-Chief aus, gibt es KEINE Datenbasis.
        # EXPANSION (bullisch) wäre hier gefährlich — nachgelagerte Agenten leiten
        # daraus aktionable "buy Tech"-Empfehlungen ab, obwohl gar keine Makro-Daten
        # vorliegen. Der Fehler ist asymmetrisch teuer: ein falsch-positives Risk-on
        # ist schlimmer als ein zu vorsichtiges Regime. Daher defensives SLOWDOWN
        # (neutralstes vorhandenes Regime, konsistent zum run()-Pfad bei leerem State)
        # + niedrige Confidence, die "kein Vertrauen / keine Daten" signalisiert.
        return MacroChiefResult(
            regime=MarketRegime.SLOWDOWN,
            regime_confidence=0.2,
            inflation=InflationAgent.default(),
            money_supply=MoneySupplyAgent.default(),
            interest_rate=InterestRateAgent.default(),
            gdp=GDPAgent.default(),
            labor_income=LaborIncomeAgent.default(),
            credit=CreditAgent.default(),
            buffett_indicator=BuffettIndicatorAgent.default(),
            status=SignalStatus.UNAVAILABLE,
        )
