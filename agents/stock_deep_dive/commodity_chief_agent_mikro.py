import asyncio

from agents.stock_deep_dive.commodity.supply_demand_agent import SupplyDemandAgent
from agents.stock_deep_dive.commodity.seasonality_agent import SeasonalityAgent
from agents.stock_deep_dive.commodity.cot_agent import COTAgent
from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import CommodityValuationRangeAgent
from core.domain.events import CommodityBottomUpChiefReady
from core.domain.models import CommodityBottomUpResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus
from core.utils.aggregation import weighted_signal


class CommodityChiefAgentMikro:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        # supply/cot provider ist None bis ein echter Adapter injiziert wird;
        # die Agenten liefern dann SignalStatus.UNAVAILABLE (nicht-brechend).
        self.supply_demand_agent             = SupplyDemandAgent(None, bus)
        self.seasonality_agent               = SeasonalityAgent(market, bus)
        self.cot_agent                       = COTAgent(None, bus)
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

        # Gewichtetes Gesamtsignal (weighted_signal ignoriert UNAVAILABLE + re-normalisiert die
        # Gewichte über die verfügbaren Sub-Signale — analog den übrigen Chiefs). Gewichte fachlich:
        # Supply/Demand (Lager/Produktion) ist der fundamentale Rohstoff-Preistreiber → höchstes Gewicht;
        # Bewertung (Perzentil/Kostenkurve) als Mean-Reversion-Anker; COT (Spekulanten, konträr)
        # bestätigend; Saisonalität bewusst am niedrigsten (verrauscht, oft kurze Historie).
        overall, confidence = weighted_signal([
            (supply_demand.signal,   0.35, supply_demand.status),
            (valuation_range.signal, 0.30, valuation_range.status),
            (cot.signal,             0.20, cot.status),
            (seasonality.signal,     0.15, seasonality.status),
        ])

        self.bus.publish(CommodityBottomUpChiefReady(source="commodity_chief_agent", payload={
            "ticker": ticker, "overall_signal": overall.value,
        }))

        return CommodityBottomUpResult(
            commodity=ticker,
            supply_demand=supply_demand,
            seasonality=seasonality,
            cot=cot,
            valuation_range=valuation_range,
            overall_signal=overall,
            confidence=confidence,
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
