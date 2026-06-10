from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentEvent:
    source: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


# --- Modus 1: Macro ---
@dataclass
class InflationDataReady(AgentEvent): pass

@dataclass
class MoneySupplyDataReady(AgentEvent): pass

@dataclass
class InterestRateDataReady(AgentEvent): pass

@dataclass
class GDPDataReady(AgentEvent): pass

@dataclass
class BuffettIndicatorReady(AgentEvent): pass

@dataclass
class LaborIncomeReady(AgentEvent): pass

@dataclass
class CreditDataReady(AgentEvent): pass

@dataclass
class MacroChiefReady(AgentEvent): pass

# --- Modus 1: Chief events (MacroChiefReady already exists above) ---
@dataclass
class CommodityChiefReady(AgentEvent): pass

@dataclass
class SentimentChiefReady(AgentEvent): pass

@dataclass
class YieldCurveChiefReady(AgentEvent): pass

@dataclass
class SectorChiefReady(AgentEvent): pass

# --- Modus 2: Chief events ---
@dataclass
class EquityChiefReady(AgentEvent): pass

@dataclass
class BondChiefReady(AgentEvent): pass

@dataclass
class IndexChiefReady(AgentEvent): pass

@dataclass
class CommodityBottomUpChiefReady(AgentEvent): pass

@dataclass
class PreciousMetalsChiefReady(AgentEvent): pass

# --- Modus 3: Chief events ---
@dataclass
class AnomalyChiefReady(AgentEvent): pass

@dataclass
class JudgmentChiefReady(AgentEvent): pass

@dataclass
class BacktesterChiefReady(AgentEvent): pass

# --- Modus 1: Commodity ---
@dataclass
class EnergyDataReady(AgentEvent): pass

@dataclass
class IndustrialMetalsDataReady(AgentEvent): pass

@dataclass
class PreciousMetalsMacroDataReady(AgentEvent): pass

@dataclass
class AgriculturalDataReady(AgentEvent): pass

# --- Modus 1: Sentiment ---
@dataclass
class VIXDataReady(AgentEvent): pass

@dataclass
class FearGreedDataReady(AgentEvent): pass

@dataclass
class PutCallDataReady(AgentEvent): pass

# --- Modus 1: Yield Curve ---
@dataclass
class YieldSpreadDataReady(AgentEvent): pass

@dataclass
class SovereignSpreadDataReady(AgentEvent): pass

# --- Modus 1: Sector ---
@dataclass
class SectorPerformanceDataReady(AgentEvent): pass

@dataclass
class SectorRotationDataReady(AgentEvent): pass

@dataclass
class CockpitResultReady(AgentEvent): pass

# --- Modus 2: Equity ---
@dataclass
class FundamentalsReady(AgentEvent): pass

@dataclass
class QualityReady(AgentEvent): pass

@dataclass
class ShortInterestReady(AgentEvent): pass

@dataclass
class InsiderDataReady(AgentEvent): pass

@dataclass
class EarningsTrendReady(AgentEvent): pass

@dataclass
class MoatReady(AgentEvent): pass

@dataclass
class ValuationRangeReady(AgentEvent): pass

# --- Modus 2: Precious Metals ---
@dataclass
class PreciousMetalsValuationReady(AgentEvent): pass

@dataclass
class PreciousMetalDataReady(AgentEvent): pass

@dataclass
class CrossMetalReady(AgentEvent): pass

# --- Modus 2: Bond ---
@dataclass
class BondMetricsReady(AgentEvent): pass

@dataclass
class BondDurationReady(AgentEvent): pass

@dataclass
class BondCreditReady(AgentEvent): pass

@dataclass
class BondSpreadReady(AgentEvent): pass

# --- Modus 2: Index ---
@dataclass
class IndexPriceReady(AgentEvent): pass

@dataclass
class IndexValuationReady(AgentEvent): pass

@dataclass
class IndexEarningsReady(AgentEvent): pass

@dataclass
class IndexBreadthReady(AgentEvent): pass

@dataclass
class IndexMomentumReady(AgentEvent): pass

@dataclass
class SectorCompositionReady(AgentEvent): pass

@dataclass
class IndexValuationRangeReady(AgentEvent): pass

# --- Modus 2: Commodity (Bottom-Up) ---
@dataclass
class SupplyDemandReady(AgentEvent): pass

@dataclass
class SeasonalityReady(AgentEvent): pass

@dataclass
class COTReady(AgentEvent): pass

@dataclass
class CommodityValuationRangeReady(AgentEvent): pass

# --- Modus 3 ---
@dataclass
class TopDownContextReady(AgentEvent): pass

@dataclass
class DeepDiveResultReady(AgentEvent): pass
