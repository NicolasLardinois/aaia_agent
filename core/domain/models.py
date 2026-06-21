from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MarketRegime(str, Enum):
    BOOM       = "Boom"
    EXPANSION  = "Aufschwung"
    SLOWDOWN   = "Abschwung"
    RECESSION  = "Rezession"
    RECOVERY   = "Erholung"
    DEPRESSION = "Depression"


class Signal(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RiskAffinity(str, Enum):
    KONSERVATIV   = "konservativ"
    NEUTRAL       = "neutral"
    RISIKOFREUDIG = "risikofreudig"


class CreditBand(str, Enum):
    SICHER  = "sicher"
    MITTEL  = "mittel"
    RISKANT = "riskant"


class SignalStatus(str, Enum):
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable"


class Recommendation(str, Enum):
    BUY      = "BUY"
    BUY_PLUS = "BUY+"
    HOLD     = "HOLD"
    SELL     = "SELL"
    NONE     = "NONE"
    SHORT    = "SHORT"   # transitional: nicht mehr von derive_recommendation ausgegeben


class ShortAction(str, Enum):
    SHORT      = "SHORT"
    SHORT_PLUS = "SHORT+"
    HOLD       = "HOLD"
    COVER      = "COVER"
    NONE       = "NONE"


class PositionState(str, Enum):
    NONE  = "none"
    LONG  = "long"
    SHORT = "short"


class ShortType(str, Enum):
    DEFENSIVE  = "DEFENSIV"
    AGGRESSIVE = "AGGRESSIV"


# ─────────────────────────────────────────────
# Modus 1 — MacroChiefAgent Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class InflationDataPoint:
    cpi: Optional[float]
    core_cpi: Optional[float]
    pce: Optional[float]          # USA only
    ppi: Optional[float]
    real_rate_10y: Optional[float]
    signal: Signal


@dataclass
class InflationSnapshot:
    usa: InflationDataPoint
    eurozone: InflationDataPoint
    switzerland: InflationDataPoint


@dataclass
class MoneySupplyDataPoint:
    m2_growth: Optional[float]
    m3_growth: Optional[float]    # EU/CH; USA has no M3
    velocity_m2: Optional[float]  # USA only
    signal: Signal


@dataclass
class MoneySupplySnapshot:
    usa: MoneySupplyDataPoint
    eurozone: MoneySupplyDataPoint
    switzerland: MoneySupplyDataPoint


@dataclass
class InterestRateDataPoint:
    policy_rate: Optional[float]
    rate_direction: str           # "rising" | "stable" | "falling"
    balance_sheet_growth: Optional[float]
    real_rate: Optional[float]    # policy_rate − CPI
    signal: Signal


@dataclass
class InterestRateSnapshot:
    usa: InterestRateDataPoint
    eurozone: InterestRateDataPoint
    switzerland: InterestRateDataPoint


@dataclass
class GDPDataPoint:
    gdp_growth: Optional[float]
    industrial_production: Optional[float]
    unemployment: Optional[float]
    consumer_sentiment: Optional[float]
    pmi: Optional[float]
    signal: Signal


@dataclass
class GDPSnapshot:
    usa: GDPDataPoint
    eurozone: GDPDataPoint
    switzerland: GDPDataPoint


@dataclass
class LaborIncomeDataPoint:
    nominal_wage_growth: Optional[float]
    real_wage_growth: Optional[float]
    signal: Signal


@dataclass
class LaborIncomeSnapshot:
    usa: LaborIncomeDataPoint
    eurozone: LaborIncomeDataPoint
    switzerland: LaborIncomeDataPoint


@dataclass
class CreditDataPoint:
    credit_growth: Optional[float]
    money_velocity: Optional[float]
    signal: Signal


@dataclass
class CreditSnapshot:
    usa: CreditDataPoint
    eurozone: CreditDataPoint
    switzerland: CreditDataPoint


@dataclass
class BuffettCountryPoint:
    ratio_pct: Optional[float]   # Marktkapitalisierung / BIP * 100
    signal: Signal
    year: Optional[int]          # None = Echtzeit (FRED); int = Weltbank-Jahreswert
    z_score: Optional[float] = None  # aktuell vs. eigene 10J-Geschichte; None = keine History


@dataclass
class BuffettIndicatorSnapshot:
    countries: dict[str, BuffettCountryPoint]  # ISO 3166 alpha-3 → Daten
    signal: Signal                             # USA-Signal für Regime/Anomalie-Nutzung
    global_median: Optional[float] = None      # Globaler Median aller Länder (für Dashboard)


@dataclass
class MacroChiefResult:
    regime: MarketRegime
    regime_confidence: float
    inflation: InflationSnapshot
    money_supply: MoneySupplySnapshot
    interest_rate: InterestRateSnapshot
    gdp: GDPSnapshot
    labor_income: LaborIncomeSnapshot
    credit: CreditSnapshot
    buffett_indicator: BuffettIndicatorSnapshot


# ─────────────────────────────────────────────
# Modus 1 — CommodityChiefAgent Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class EnergySnapshot:
    wti_usd: Optional[float]
    brent_usd: Optional[float]
    natural_gas_usd: Optional[float]
    signal: Signal


@dataclass
class IndustrialMetalsSnapshot:
    copper_usd: Optional[float]
    aluminium_usd: Optional[float]
    zinc_usd: Optional[float]
    nickel_usd: Optional[float]
    signal: Signal


@dataclass
class PreciousMetalsMacroSnapshot:
    gold_usd: Optional[float]
    silver_usd: Optional[float]
    platinum_usd: Optional[float]
    palladium_usd: Optional[float]
    gold_silver_ratio: Optional[float]
    gold_platinum_ratio: Optional[float]
    signal: Signal


@dataclass
class AgriculturalSnapshot:
    wheat_usd: Optional[float]
    corn_usd: Optional[float]
    soy_usd: Optional[float]
    coffee_usd: Optional[float]
    sugar_usd: Optional[float]
    cotton_usd: Optional[float]
    orange_juice_usd: Optional[float]
    signal: Signal


@dataclass
class CommodityChiefResult:
    energy: EnergySnapshot
    industrial_metals: IndustrialMetalsSnapshot
    precious_metals: PreciousMetalsMacroSnapshot
    agricultural: AgriculturalSnapshot
    signal: Signal = Signal.NEUTRAL


# ─────────────────────────────────────────────
# Modus 1 — SentimentChiefAgent Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class VIXSnapshot:
    vix: Optional[float]
    vstoxx: Optional[float]
    signal: Signal


@dataclass
class FearGreedSnapshot:
    value: Optional[float]        # 0–100
    label: str                    # "Extreme Fear" | "Fear" | "Neutral" | "Greed" | "Extreme Greed"
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class PutCallSnapshot:
    ratio: Optional[float]
    signal: Signal


@dataclass
class SentimentChiefResult:
    vix: VIXSnapshot
    fear_greed: FearGreedSnapshot
    put_call: PutCallSnapshot
    signal: Signal = Signal.NEUTRAL


# ─────────────────────────────────────────────
# Modus 1 — YieldCurveChiefAgent Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class YieldSpreadDataPoint:
    spread_10y2y: Optional[float]
    spread_10y3m: Optional[float]
    spread_30y10y: Optional[float]
    inverted: bool
    signal: Signal


@dataclass
class YieldSpreadSnapshot:
    usa: YieldSpreadDataPoint
    eurozone: YieldSpreadDataPoint
    switzerland: YieldSpreadDataPoint


@dataclass
class SovereignSpreadSnapshot:
    btp_bund: Optional[float]     # Italy vs Germany (bps) — backward compat
    oat_bund: Optional[float]     # France vs Germany — backward compat
    bonos_bund: Optional[float]   # Spain vs Germany — backward compat
    signal: Signal
    spreads_by_country: dict = field(default_factory=dict)   # {"{CC}_10y": bp}


@dataclass
class YieldCurveChiefResult:
    yield_spreads: YieldSpreadSnapshot
    sovereign_spreads: SovereignSpreadSnapshot
    signal: Signal = Signal.NEUTRAL


# ─────────────────────────────────────────────
# Modus 1 — SectorChiefAgent Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class SectorPerformanceSnapshot:
    usa: dict[str, float]
    eurozone: dict[str, float]
    leading_usa: str
    lagging_usa: str
    leading_eu: str
    lagging_eu: str


@dataclass
class SectorRotationSnapshot:
    recommended: list[str]
    avoid: list[str]
    alignment: str                # "aligned" | "contradicting" | "neutral"
    signal: Signal


@dataclass
class SectorChiefResult:
    performance: SectorPerformanceSnapshot
    rotation: SectorRotationSnapshot


# ─────────────────────────────────────────────
# Modus 1 — CockpitResult
# ─────────────────────────────────────────────

@dataclass
class CockpitResult:
    macro: MacroChiefResult
    commodities: CommodityChiefResult
    sentiment: SentimentChiefResult
    yield_curve: YieldCurveChiefResult
    sectors: SectorChiefResult


# ─────────────────────────────────────────────
# Modus 2 — Equity Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class FundamentalsSnapshot:
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    shiller_cape: Optional[float]
    peg_ratio: Optional[float]
    ev_ebitda: Optional[float]
    ev_revenue: Optional[float]
    price_book: Optional[float]
    price_sales: Optional[float]
    price_fcf: Optional[float]
    dividend_yield: Optional[float]
    wacc: Optional[float]
    revenue_cagr_3y: Optional[float]
    operating_margin: Optional[float]
    gross_margin: Optional[float]
    debt_to_equity: Optional[float]
    signal: Signal


@dataclass
class QualitySnapshot:
    gross_margin: Optional[float]
    operating_margin: Optional[float]
    net_margin: Optional[float]
    fcf_margin: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    roic: Optional[float]
    debt_to_equity: Optional[float]
    net_debt_ebitda: Optional[float]
    interest_coverage: Optional[float]
    current_ratio: Optional[float]
    altman_z: Optional[float]
    signal: Signal


@dataclass
class ShortInterestSnapshot:
    short_float_pct: Optional[float]
    days_to_cover: Optional[float]
    signal: Signal


@dataclass
class InsiderSnapshot:
    net_direction: str
    recent_transactions: int
    signal: Signal


@dataclass
class EarningsTrendSnapshot:
    beat_rate: Optional[float]
    estimate_revision: str
    signal: Signal


@dataclass
class MoatScore:
    score: int
    evidence: str


@dataclass
class MoatSnapshot:
    intangible_assets: MoatScore
    switching_costs: MoatScore
    network_effects: MoatScore
    cost_advantages: MoatScore
    efficient_scale: MoatScore
    total_score: int
    overall: str                  # "wide" | "narrow" | "none"
    llm_reasoning: str
    signal: Signal


@dataclass
class ValuationMethod:
    name: str
    low: float
    high: float
    currency: str = "USD"


@dataclass
class ValuationRangeSnapshot:
    methods: list[ValuationMethod]
    combined_low: float
    combined_high: float
    current_price: Optional[float]
    position: str                 # "undervalued" | "fair" | "overvalued" | "unknown"
    signal: Signal


@dataclass
class EquityChiefResult:
    fundamentals: FundamentalsSnapshot
    quality: QualitySnapshot
    short_interest: ShortInterestSnapshot
    insider: InsiderSnapshot
    earnings_trend: EarningsTrendSnapshot
    moat: MoatSnapshot
    valuation_range: ValuationRangeSnapshot


# ─────────────────────────────────────────────
# Modus 2 — Precious Metals Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class PreciousMetalSnapshot:
    metal: str
    price_usd: Optional[float]
    performance: dict[str, float]
    rsi: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    stock_to_flow: Optional[float]
    real_yield_correlation: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class CrossMetalSnapshot:
    gold_silver_ratio: Optional[float]
    gold_platinum_ratio: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class PreciousMetalsResult:
    metal: str
    price_analysis: PreciousMetalSnapshot
    cross_metal: CrossMetalSnapshot
    valuation_range: ValuationRangeSnapshot
    cot_signal: Signal
    currency_impact: dict[str, float]


# ─────────────────────────────────────────────
# Modus 2 — Bond Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class BondMetricsSnapshot:
    bond_type: str                # "government" | "corporate"
    current_price: Optional[float]
    coupon: Optional[float]
    maturity_years: Optional[float]
    ytm: Optional[float]
    ytc: Optional[float]
    current_yield: Optional[float]
    real_yield: Optional[float]
    country: Optional[str]        # government only
    breakeven_inflation: Optional[float]  # government USA only (TIPS)
    issuer: Optional[str]         # corporate only
    sector: Optional[str]         # corporate only
    signal: Signal


@dataclass
class BondDurationSnapshot:
    macaulay_duration: Optional[float]
    modified_duration: Optional[float]
    convexity: Optional[float]
    dv01: Optional[float]
    signal: Signal


@dataclass
class BondCreditSnapshot:
    moodys: Optional[str]
    sp: Optional[str]
    fitch: Optional[str]
    category: str                 # "investment_grade" | "high_yield" | "junk"
    trend: str                    # "upgrade" | "stable" | "downgrade"
    default_probability: Optional[float]
    signal: Signal


@dataclass
class BondSpreadSnapshot:
    spread_bps: Optional[float]
    oas: Optional[float]
    z_spread: Optional[float]
    spread_trend: str             # "tightening" | "stable" | "widening"
    signal: Signal


@dataclass
class BondResult:
    ticker: str
    bond_type: str
    metrics: BondMetricsSnapshot
    duration: BondDurationSnapshot
    credit: BondCreditSnapshot
    spread: BondSpreadSnapshot


# ─────────────────────────────────────────────
# Modus 2 — Index Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class IndexPriceSnapshot:
    current_price: Optional[float]
    perf_1w: Optional[float]
    perf_1m: Optional[float]
    perf_3m: Optional[float]
    perf_ytd: Optional[float]
    perf_1y: Optional[float]
    perf_3y: Optional[float]
    perf_5y: Optional[float]
    high_52w: Optional[float]
    low_52w: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class IndexValuationSnapshot:
    pe_trailing: Optional[float]
    pe_forward: Optional[float]
    shiller_cape: Optional[float]
    dividend_yield: Optional[float]
    ev_ebitda: Optional[float]
    signal: Signal


@dataclass
class IndexEarningsSnapshot:
    eps_growth_1y: Optional[float]
    revenue_growth_1y: Optional[float]
    operating_margin: Optional[float]
    estimate_revision: str            # "up" | "stable" | "down"
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class IndexBreadthSnapshot:
    pct_above_ma50: Optional[float]
    pct_above_ma200: Optional[float]
    advance_decline_ratio: Optional[float]
    new_highs: Optional[int]
    new_lows: Optional[int]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class IndexMomentumSnapshot:
    rsi_14: Optional[float]
    ma50: Optional[float]
    ma200: Optional[float]
    golden_cross: Optional[bool]
    relative_strength: Optional[float]
    signal: Signal


@dataclass
class SectorCompositionSnapshot:
    top_sector: Optional[str]
    top_sector_weight: Optional[float]
    top_holding: Optional[str]
    top_holding_weight: Optional[float]
    top_10_concentration: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class IndexValuationRangeSnapshot:
    eps_estimate: Optional[float]
    pe_historical_low: Optional[float]
    pe_historical_high: Optional[float]
    price_low: Optional[float]
    price_mid: Optional[float]
    price_high: Optional[float]
    current_price: Optional[float]
    position: str                     # "undervalued" | "fair" | "overvalued"
    signal: Signal


@dataclass
class IndexResult:
    ticker: str
    price: IndexPriceSnapshot
    valuation: IndexValuationSnapshot
    earnings: IndexEarningsSnapshot
    breadth: IndexBreadthSnapshot
    momentum: IndexMomentumSnapshot
    composition: SectorCompositionSnapshot
    valuation_range: IndexValuationRangeSnapshot


# ─────────────────────────────────────────────
# Modus 2 — Commodity Bottom-Up Sub-Snapshots
# ─────────────────────────────────────────────

@dataclass
class SupplyDemandSnapshot:
    inventory_current: Optional[float]
    inventory_avg_5y: Optional[float]
    inventory_pct_vs_avg: Optional[float]
    production_change_yoy: Optional[float]
    stock_to_flow: Optional[float]        # Gesamtbestand / Jahresproduktion
    stock_to_flow_signal: Optional[str]   # "scarce" | "normal" | "abundant"
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class SeasonalitySnapshot:
    current_month_bias: str           # "bullish" | "neutral" | "bearish"
    avg_return_this_month: Optional[float]
    positive_years_pct: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class COTSnapshot:
    net_speculative_long: Optional[float]
    net_speculative_pct_oi: Optional[float]
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class CommodityValuationRangeSnapshot:
    current_price: Optional[float]
    price_low_5y: Optional[float]
    price_high_5y: Optional[float]
    percentile_5y: Optional[float]
    percentile_10y: Optional[float]
    production_cost_low: Optional[float]
    production_cost_high: Optional[float]
    position: str                     # "cheap" | "fair" | "expensive"
    signal: Signal
    status: SignalStatus = SignalStatus.AVAILABLE


@dataclass
class CommodityBottomUpResult:
    commodity: str
    supply_demand: SupplyDemandSnapshot
    seasonality: SeasonalitySnapshot
    cot: COTSnapshot
    valuation_range: CommodityValuationRangeSnapshot


# ─────────────────────────────────────────────
# Modus 2 — BottomUpResult
# ─────────────────────────────────────────────

@dataclass
class BottomUpResult:
    ticker: str
    asset_class: str              # "equity" | "bond" | "commodity" | "precious_metal" | "index"
    fundamentals: Optional[FundamentalsSnapshot]
    quality: Optional[QualitySnapshot]
    short_interest: Optional[ShortInterestSnapshot]
    insider: Optional[InsiderSnapshot]
    earnings_trend: Optional[EarningsTrendSnapshot]
    moat: Optional[MoatSnapshot]
    valuation_range: Optional[ValuationRangeSnapshot]
    precious_metals: Optional[PreciousMetalsResult]
    bond: Optional[BondResult]
    index: Optional[IndexResult]
    commodity_deep: Optional[CommodityBottomUpResult]


# ─────────────────────────────────────────────
# Modus 2 — AnomalyReport
# ─────────────────────────────────────────────

@dataclass
class AnomalyReport:
    has_anomalies: bool
    statistical: list[str]
    contradictions: list[str]
    severity: str   # "none" | "low" | "medium" | "high"
    summary: str
    direction: str = "neutral"   # "bearish" | "bullish" | "neutral"

    @staticmethod
    def empty() -> "AnomalyReport":
        return AnomalyReport(
            has_anomalies=False,
            statistical=[],
            contradictions=[],
            severity="none",
            summary="Keine Anomalien erkannt.",
            direction="neutral",
        )


# ─────────────────────────────────────────────
# Modus 3 — Kombinations-Urteil
# ─────────────────────────────────────────────

@dataclass
class InvestmentRecommendation:
    action: Recommendation
    short_type: Optional[ShortType]
    short_warning: Optional[str]
    confidence: float
    reasoning: str


@dataclass
class ShortAssessment:
    asset_class: str
    short_action: ShortAction
    confidence: float
    archetypes: list[str]
    thesis_flags: list[str]
    regime_effect: str            # "headwind" | "neutral" | "tailwind"
    squeeze_risk: str             # "low" | "elevated" | "high"
    hard_to_borrow: bool
    borrow_rate_manual: Optional[float] = None
    suggested_size_pct: Optional[float] = None
    stop_pct: Optional[float] = None


@dataclass
class ConflictResolution:
    verdict: str       # "EXIT" | "HOLD" | "REVERSE"
    reasoning: str


@dataclass
class DeepDiveResult:
    ticker: str
    asset_class: str
    market: str                       # neu
    top_down_context: str
    top_down_available: bool
    judgment: str
    alignment: str
    recommendation: InvestmentRecommendation
    bottom_up: Optional[BottomUpResult] = None
    dominant_signal: str = "neutral"
    confidence: float = 0.65
    xai_explanation: str = ""
    top_down_anomaly: Optional["AnomalyReport"] = None
    bottom_up_anomaly: Optional["AnomalyReport"] = None
    short_action: ShortAction = ShortAction.NONE
    short_assessment: Optional["ShortAssessment"] = None
    conflict: bool = False
    conflict_reason: str = ""
    conflict_resolution: Optional["ConflictResolution"] = None
