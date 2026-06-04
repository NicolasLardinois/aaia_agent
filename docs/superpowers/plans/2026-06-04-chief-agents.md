# ChiefAgents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a ChiefAgent layer between orchestrators and sub-agents — each ChiefAgent owns its sub-agents, runs them in parallel with full resilience (both levels), and publishes a ChiefReady event.

**Architecture:** Three orchestrators (TopDown, BottomUp, Judgment) each delegate to ChiefAgents. Each ChiefAgent instantiates its sub-agents, gathers them with `return_exceptions=True`, falls back to `default()` on failure, and publishes a domain event. Orchestrators also use `return_exceptions=True` when gathering chiefs.

**Tech Stack:** Python 3.11+, asyncio, pytest, unittest.mock (MagicMock, AsyncMock)

---

## File Map

### Created
| File | Class | Returns |
|------|-------|---------|
| `agents/market_cockpit/macro_chief_agent.py` | `MacroChiefAgent` | `MacroChiefResult` |
| `agents/market_cockpit/commodity_chief_agent.py` | `CommodityChiefAgent` | `CommodityChiefResult` |
| `agents/market_cockpit/sentiment_chief_agent.py` | `SentimentChiefAgent` | `SentimentChiefResult` |
| `agents/market_cockpit/yield_curve_chief_agent.py` | `YieldCurveChiefAgent` | `YieldCurveChiefResult` |
| `agents/market_cockpit/sector_chief_agent.py` | `SectorChiefAgent` | `SectorChiefResult` |
| `agents/stock_deep_dive/equity_chief_agent.py` | `EquityChiefAgent` | `EquityChiefResult` |
| `agents/stock_deep_dive/bond_chief_agent.py` | `BondChiefAgent` | `BondResult` |
| `agents/stock_deep_dive/index_chief_agent.py` | `IndexChiefAgent` | `IndexResult` |
| `agents/stock_deep_dive/commodity_chief_agent.py` | `CommodityChiefAgent` | `CommodityBottomUpResult` |
| `agents/stock_deep_dive/precious_metals_chief_agent.py` | `PreciousMetalsChiefAgent` | `PreciousMetalsResult` |
| `agents/anomaly_chief_agent.py` | `AnomalyChiefAgent` | `tuple[AnomalyReport, AnomalyReport]` |
| `agents/judgment_chief_agent.py` | `JudgmentChiefAgent` | `DeepDiveResult` |
| `agents/backtester_chief_agent.py` | `BacktesterChiefAgent` | `None` (run) / `dict` (load_context) |
| `tests/test_chief_agents_cockpit.py` | — | — |
| `tests/test_chief_agents_deep_dive.py` | — | — |
| `tests/test_chief_agents_judgment.py` | — | — |

### Modified
| File | Change |
|------|--------|
| `core/domain/models.py` | Add `EquityChiefResult` dataclass |
| `core/domain/events.py` | Add 12 ChiefReady event classes |
| `orchestrators/top_down_orchestrator.py` | Replace 17 agents with 5 ChiefAgents |
| `orchestrators/bottom_up_orchestrator.py` | Replace 21 agents with 5 ChiefAgents |
| `orchestrators/judgment_orchestrator.py` | Replace 3 agents with 3 ChiefAgents |

---

## Task 1: Foundation — models.py + events.py

**Files:**
- Modify: `core/domain/models.py` (after line 412, before `BottomUpResult`)
- Modify: `core/domain/events.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_chief_agents_cockpit.py
from core.domain.models import EquityChiefResult, Signal
from core.domain.models import FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot
from core.domain.models import InsiderSnapshot, EarningsTrendSnapshot, MoatSnapshot, MoatScore, ValuationRangeSnapshot

def test_equity_chief_result_fields():
    result = EquityChiefResult(
        fundamentals=FundamentalsSnapshot(
            pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
            ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
            price_fcf=None, dividend_yield=None, wacc=None,
            revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
            debt_to_equity=None, signal=Signal.NEUTRAL,
        ),
        quality=QualitySnapshot(
            gross_margin=None, operating_margin=None, net_margin=None,
            fcf_margin=None, roe=None, roa=None, roic=None,
            debt_to_equity=None, net_debt_ebitda=None, interest_coverage=None,
            current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
        ),
        short_interest=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL),
        insider=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL),
        earnings_trend=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL),
        moat=MoatSnapshot(
            intangible_assets=MoatScore(score=0, evidence=""),
            switching_costs=MoatScore(score=0, evidence=""),
            network_effects=MoatScore(score=0, evidence=""),
            cost_advantages=MoatScore(score=0, evidence=""),
            efficient_scale=MoatScore(score=0, evidence=""),
            total_score=0, overall="none", llm_reasoning="", signal=Signal.NEUTRAL,
        ),
        valuation_range=ValuationRangeSnapshot(
            methods=[], combined_low=0.0, combined_high=0.0,
            current_price=None, position="unknown", signal=Signal.NEUTRAL,
        ),
    )
    assert result.fundamentals.signal == Signal.NEUTRAL
    assert result.moat.overall == "none"
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_equity_chief_result_fields -v
# Expected: ImportError — EquityChiefResult does not exist yet
```

- [ ] **Step 3: Add `EquityChiefResult` to `core/domain/models.py`**

Insert after line 412 (after `ValuationRangeSnapshot`, before the `# Modus 2 — Precious Metals` comment):

```python
@dataclass
class EquityChiefResult:
    fundamentals: FundamentalsSnapshot
    quality: QualitySnapshot
    short_interest: ShortInterestSnapshot
    insider: InsiderSnapshot
    earnings_trend: EarningsTrendSnapshot
    moat: MoatSnapshot
    valuation_range: ValuationRangeSnapshot
```

- [ ] **Step 4: Write failing test for events**

Add to `tests/test_chief_agents_cockpit.py`:

```python
from core.domain.events import (
    MacroChiefReady, CommodityChiefReady, SentimentChiefReady,
    YieldCurveChiefReady, SectorChiefReady,
    EquityChiefReady, BondChiefReady, IndexChiefReady,
    CommodityBottomUpChiefReady, PreciousMetalsChiefReady,
    AnomalyChiefReady, JudgmentChiefReady, BacktesterChiefReady,
)

def test_chief_events_importable():
    e = CommodityChiefReady(source="test", payload={})
    assert e.source == "test"
```

- [ ] **Step 5: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_chief_events_importable -v
# Expected: ImportError — CommodityChiefReady does not exist yet
```

- [ ] **Step 6: Add 12 new events to `core/domain/events.py`**

After the existing `class MacroChiefReady(AgentEvent): pass` line, add:

```python
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
```

- [ ] **Step 7: Run both tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -v
# Expected: 2 passed
```

- [ ] **Step 8: Commit**

```bash
git add core/domain/models.py core/domain/events.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add EquityChiefResult and 12 ChiefReady events"
```

---

## Task 2: MacroChiefAgent

**Files:**
- Create: `agents/market_cockpit/macro_chief_agent.py`
- Test: `tests/test_chief_agents_cockpit.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_cockpit.py`:

```python
import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from core.domain.models import (
    MacroChiefResult, MarketRegime,
    InflationSnapshot, MoneySupplySnapshot, InterestRateSnapshot,
    GDPSnapshot, ShillerCAPESnapshot, LaborIncomeSnapshot, CreditSnapshot,
    InflationDataPoint, MoneySupplyDataPoint, InterestRateDataPoint,
    GDPDataPoint, ShillerCAPEDataPoint, LaborIncomeDataPoint, CreditDataPoint,
    Signal,
)

def _neutral_inflation():
    dp = InflationDataPoint(cpi=None, core_cpi=None, pce=None, ppi=None, real_rate_10y=None, signal=Signal.NEUTRAL)
    return InflationSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_money_supply():
    dp = MoneySupplyDataPoint(m2_growth=None, m3_growth=None, velocity_m2=None, signal=Signal.NEUTRAL)
    return MoneySupplySnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_interest_rate():
    dp = InterestRateDataPoint(policy_rate=None, rate_direction="stable", balance_sheet_growth=None, real_rate=None, signal=Signal.NEUTRAL)
    return InterestRateSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_gdp():
    dp = GDPDataPoint(gdp_growth=None, industrial_production=None, unemployment=None, consumer_sentiment=None, pmi=None, signal=Signal.NEUTRAL)
    return GDPSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_shiller():
    dp = ShillerCAPEDataPoint(cape=None, historical_avg=20.0, deviation_pct=None, signal=Signal.NEUTRAL)
    return ShillerCAPESnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_labor():
    dp = LaborIncomeDataPoint(nominal_wage_growth=None, real_wage_growth=None, signal=Signal.NEUTRAL)
    return LaborIncomeSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def _neutral_credit():
    dp = CreditDataPoint(credit_growth=None, money_velocity=None, signal=Signal.NEUTRAL)
    return CreditSnapshot(usa=dp, eurozone=dp, switzerland=dp)


def test_macro_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    macro.get_economic_state = MagicMock(return_value={})
    ecb = MagicMock()
    snb = MagicMock()
    market = MagicMock()

    chief = MacroChiefAgent(macro, ecb, snb, market, bus)
    chief.inflation_agent.run     = AsyncMock(return_value=_neutral_inflation())
    chief.money_supply_agent.run  = AsyncMock(return_value=_neutral_money_supply())
    chief.interest_rate_agent.run = AsyncMock(return_value=_neutral_interest_rate())
    chief.gdp_agent.run           = AsyncMock(return_value=_neutral_gdp())
    chief.shiller_cape_agent.run  = AsyncMock(return_value=_neutral_shiller())
    chief.labor_income_agent.run  = AsyncMock(return_value=_neutral_labor())
    chief.credit_agent.run        = AsyncMock(return_value=_neutral_credit())

    result = asyncio.run(chief.run())
    assert isinstance(result, MacroChiefResult)
    assert isinstance(result.regime, MarketRegime)
    bus.publish.assert_called_once()


def test_macro_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    macro.get_economic_state = MagicMock(return_value={})
    ecb = MagicMock()
    snb = MagicMock()
    market = MagicMock()

    chief = MacroChiefAgent(macro, ecb, snb, market, bus)
    chief.inflation_agent.run     = AsyncMock(side_effect=RuntimeError("API down"))
    chief.money_supply_agent.run  = AsyncMock(return_value=_neutral_money_supply())
    chief.interest_rate_agent.run = AsyncMock(return_value=_neutral_interest_rate())
    chief.gdp_agent.run           = AsyncMock(return_value=_neutral_gdp())
    chief.shiller_cape_agent.run  = AsyncMock(return_value=_neutral_shiller())
    chief.labor_income_agent.run  = AsyncMock(return_value=_neutral_labor())
    chief.credit_agent.run        = AsyncMock(return_value=_neutral_credit())

    result = asyncio.run(chief.run())
    assert isinstance(result, MacroChiefResult)  # did not crash


def test_macro_chief_default():
    result = MacroChiefAgent.default()
    assert isinstance(result, MacroChiefResult)
    assert result.regime == MarketRegime.EXPANSION
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_macro_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/market_cockpit/macro_chief_agent.py`**

```python
import asyncio

from agents.market_cockpit.macro.inflation_agent import InflationAgent
from agents.market_cockpit.macro.money_supply_agent import MoneySupplyAgent
from agents.market_cockpit.macro.interest_rate_agent import InterestRateAgent
from agents.market_cockpit.macro.gdp_agent import GDPAgent
from agents.market_cockpit.macro.shiller_cape_agent import ShillerCAPEAgent
from agents.market_cockpit.macro.labor_income_agent import LaborIncomeAgent
from agents.market_cockpit.macro.credit_agent import CreditAgent
from core.domain.events import MacroChiefReady
from core.domain.models import MacroChiefResult, MarketRegime
from core.domain.regime import RegimeDetector
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, MarketDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus


class MacroChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
    ):
        self._macro    = macro
        self._detector = RegimeDetector()
        self.bus       = bus

        self.inflation_agent     = InflationAgent(macro, ecb, snb, bus)
        self.money_supply_agent  = MoneySupplyAgent(macro, ecb, snb, bus)
        self.interest_rate_agent = InterestRateAgent(macro, ecb, snb, bus)
        self.gdp_agent           = GDPAgent(macro, ecb, snb, bus)
        self.shiller_cape_agent  = ShillerCAPEAgent(market, bus)
        self.labor_income_agent  = LaborIncomeAgent(macro, bus)
        self.credit_agent        = CreditAgent(macro, bus)

    async def run(self) -> MacroChiefResult:
        results = await asyncio.gather(
            self.inflation_agent.run(),
            self.money_supply_agent.run(),
            self.interest_rate_agent.run(),
            self.gdp_agent.run(),
            self.shiller_cape_agent.run(),
            self.labor_income_agent.run(),
            self.credit_agent.run(),
            asyncio.to_thread(self._macro.get_economic_state),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        inflation     = _safe(results[0], InflationAgent.default())
        money_supply  = _safe(results[1], MoneySupplyAgent.default())
        interest_rate = _safe(results[2], InterestRateAgent.default())
        gdp           = _safe(results[3], GDPAgent.default())
        shiller_cape  = _safe(results[4], ShillerCAPEAgent.default())
        labor_income  = _safe(results[5], LaborIncomeAgent.default())
        credit        = _safe(results[6], CreditAgent.default())
        state         = _safe(results[7], {})

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
            shiller_cape=shiller_cape,
            labor_income=labor_income,
            credit=credit,
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
            shiller_cape=ShillerCAPEAgent.default(),
            labor_income=LaborIncomeAgent.default(),
            credit=CreditAgent.default(),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -k "macro_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/macro_chief_agent.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add MacroChiefAgent"
```

---

## Task 3: CommodityChiefAgent (Market Cockpit)

**Files:**
- Create: `agents/market_cockpit/commodity_chief_agent.py`
- Test: `tests/test_chief_agents_cockpit.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_cockpit.py`:

```python
from agents.market_cockpit.commodity_chief_agent import CommodityChiefAgent
from core.domain.models import CommodityChiefResult, EnergySnapshot, IndustrialMetalsSnapshot, PreciousMetalsMacroSnapshot, AgriculturalSnapshot

def _neutral_energy():
    return EnergySnapshot(wti_usd=None, brent_usd=None, natural_gas_usd=None, signal=Signal.NEUTRAL)

def _neutral_industrial():
    return IndustrialMetalsSnapshot(copper_usd=None, aluminium_usd=None, zinc_usd=None, nickel_usd=None, signal=Signal.NEUTRAL)

def _neutral_precious_macro():
    return PreciousMetalsMacroSnapshot(gold_usd=None, silver_usd=None, platinum_usd=None, palladium_usd=None, gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL)

def _neutral_agricultural():
    return AgriculturalSnapshot(wheat_usd=None, corn_usd=None, soy_usd=None, coffee_usd=None, sugar_usd=None, cotton_usd=None, orange_juice_usd=None, signal=Signal.NEUTRAL)


def test_commodity_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgent(market, bus)
    chief.energy_agent.run           = AsyncMock(return_value=_neutral_energy())
    chief.industrial_agent.run       = AsyncMock(return_value=_neutral_industrial())
    chief.precious_metals_agent.run  = AsyncMock(return_value=_neutral_precious_macro())
    chief.agricultural_agent.run     = AsyncMock(return_value=_neutral_agricultural())

    result = asyncio.run(chief.run())
    assert isinstance(result, CommodityChiefResult)
    bus.publish.assert_called_once()


def test_commodity_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityChiefAgent(market, bus)
    chief.energy_agent.run           = AsyncMock(side_effect=RuntimeError("timeout"))
    chief.industrial_agent.run       = AsyncMock(return_value=_neutral_industrial())
    chief.precious_metals_agent.run  = AsyncMock(return_value=_neutral_precious_macro())
    chief.agricultural_agent.run     = AsyncMock(return_value=_neutral_agricultural())

    result = asyncio.run(chief.run())
    assert isinstance(result, CommodityChiefResult)


def test_commodity_chief_default():
    result = CommodityChiefAgent.default()
    assert isinstance(result, CommodityChiefResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_commodity_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/market_cockpit/commodity_chief_agent.py`**

```python
import asyncio

from agents.market_cockpit.commodity.energy_agent import EnergyAgent
from agents.market_cockpit.commodity.industrial_metals_agent import IndustrialMetalsAgent
from agents.market_cockpit.commodity.precious_metals_macro_agent import PreciousMetalsMacroAgent
from agents.market_cockpit.commodity.agricultural_agent import AgriculturalAgent
from core.domain.events import CommodityChiefReady
from core.domain.models import CommodityChiefResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class CommodityChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.energy_agent          = EnergyAgent(market, bus)
        self.industrial_agent      = IndustrialMetalsAgent(market, bus)
        self.precious_metals_agent = PreciousMetalsMacroAgent(market, bus)
        self.agricultural_agent    = AgriculturalAgent(market, bus)

    async def run(self) -> CommodityChiefResult:
        results = await asyncio.gather(
            self.energy_agent.run(),
            self.industrial_agent.run(),
            self.precious_metals_agent.run(),
            self.agricultural_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        energy            = _safe(results[0], EnergyAgent.default())
        industrial_metals = _safe(results[1], IndustrialMetalsAgent.default())
        precious_metals   = _safe(results[2], PreciousMetalsMacroAgent.default())
        agricultural      = _safe(results[3], AgriculturalAgent.default())

        self.bus.publish(CommodityChiefReady(source="commodity_chief_agent", payload={}))

        return CommodityChiefResult(
            energy=energy,
            industrial_metals=industrial_metals,
            precious_metals=precious_metals,
            agricultural=agricultural,
        )

    @staticmethod
    def default() -> CommodityChiefResult:
        return CommodityChiefResult(
            energy=EnergyAgent.default(),
            industrial_metals=IndustrialMetalsAgent.default(),
            precious_metals=PreciousMetalsMacroAgent.default(),
            agricultural=AgriculturalAgent.default(),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -k "commodity_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/commodity_chief_agent.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add CommodityChiefAgent (market cockpit)"
```

---

## Task 4: SentimentChiefAgent

**Files:**
- Create: `agents/market_cockpit/sentiment_chief_agent.py`
- Test: `tests/test_chief_agents_cockpit.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_cockpit.py`:

```python
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from core.domain.models import SentimentChiefResult, VIXSnapshot, FearGreedSnapshot, PutCallSnapshot

def test_sentiment_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = SentimentChiefAgent(market, bus)
    chief.vix_agent.run        = AsyncMock(return_value=VIXSnapshot(vix=None, vstoxx=None, signal=Signal.NEUTRAL))
    chief.fear_greed_agent.run = AsyncMock(return_value=FearGreedSnapshot(value=None, label="Neutral", signal=Signal.NEUTRAL))
    chief.put_call_agent.run   = AsyncMock(return_value=PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, SentimentChiefResult)
    bus.publish.assert_called_once()


def test_sentiment_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = SentimentChiefAgent(market, bus)
    chief.vix_agent.run        = AsyncMock(side_effect=RuntimeError("down"))
    chief.fear_greed_agent.run = AsyncMock(return_value=FearGreedSnapshot(value=None, label="Neutral", signal=Signal.NEUTRAL))
    chief.put_call_agent.run   = AsyncMock(return_value=PutCallSnapshot(ratio=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, SentimentChiefResult)


def test_sentiment_chief_default():
    result = SentimentChiefAgent.default()
    assert isinstance(result, SentimentChiefResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_sentiment_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/market_cockpit/sentiment_chief_agent.py`**

```python
import asyncio

from agents.market_cockpit.sentiment.vix_agent import VIXAgent
from agents.market_cockpit.sentiment.fear_greed_agent import FearGreedAgent
from agents.market_cockpit.sentiment.put_call_agent import PutCallAgent
from core.domain.events import SentimentChiefReady
from core.domain.models import SentimentChiefResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class SentimentChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.vix_agent        = VIXAgent(market, bus)
        self.fear_greed_agent = FearGreedAgent(bus)
        self.put_call_agent   = PutCallAgent(market, bus)

    async def run(self) -> SentimentChiefResult:
        results = await asyncio.gather(
            self.vix_agent.run(),
            self.fear_greed_agent.run(),
            self.put_call_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        vix        = _safe(results[0], VIXAgent.default())
        fear_greed = _safe(results[1], FearGreedAgent.default())
        put_call   = _safe(results[2], PutCallAgent.default())

        self.bus.publish(SentimentChiefReady(source="sentiment_chief_agent", payload={}))

        return SentimentChiefResult(vix=vix, fear_greed=fear_greed, put_call=put_call)

    @staticmethod
    def default() -> SentimentChiefResult:
        return SentimentChiefResult(
            vix=VIXAgent.default(),
            fear_greed=FearGreedAgent.default(),
            put_call=PutCallAgent.default(),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -k "sentiment_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/sentiment_chief_agent.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add SentimentChiefAgent"
```

---

## Task 5: YieldCurveChiefAgent

**Files:**
- Create: `agents/market_cockpit/yield_curve_chief_agent.py`
- Test: `tests/test_chief_agents_cockpit.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_cockpit.py`:

```python
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from core.domain.models import YieldCurveChiefResult, YieldSpreadSnapshot, SovereignSpreadSnapshot, YieldSpreadDataPoint

def _neutral_yield_spread():
    dp = YieldSpreadDataPoint(spread_10y2y=None, spread_10y3m=None, spread_30y10y=None, inverted=False, signal=Signal.NEUTRAL)
    return YieldSpreadSnapshot(usa=dp, eurozone=dp, switzerland=dp)

def test_yield_curve_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    ecb = MagicMock()
    snb = MagicMock()
    chief = YieldCurveChiefAgent(macro, ecb, snb, bus)
    chief.yield_spread_agent.run     = AsyncMock(return_value=_neutral_yield_spread())
    chief.sovereign_spread_agent.run = AsyncMock(return_value=SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, YieldCurveChiefResult)
    bus.publish.assert_called_once()


def test_yield_curve_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    ecb = MagicMock()
    snb = MagicMock()
    chief = YieldCurveChiefAgent(macro, ecb, snb, bus)
    chief.yield_spread_agent.run     = AsyncMock(side_effect=RuntimeError("timeout"))
    chief.sovereign_spread_agent.run = AsyncMock(return_value=SovereignSpreadSnapshot(btp_bund=None, oat_bund=None, bonos_bund=None, signal=Signal.NEUTRAL))

    result = asyncio.run(chief.run())
    assert isinstance(result, YieldCurveChiefResult)


def test_yield_curve_chief_default():
    result = YieldCurveChiefAgent.default()
    assert isinstance(result, YieldCurveChiefResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_yield_curve_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/market_cockpit/yield_curve_chief_agent.py`**

```python
import asyncio

from agents.market_cockpit.yield_curve.yield_spread_agent import YieldSpreadAgent
from agents.market_cockpit.yield_curve.sovereign_spread_agent import SovereignSpreadAgent
from core.domain.events import YieldCurveChiefReady
from core.domain.models import YieldCurveChiefResult
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus


class YieldCurveChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        ecb: EcbDataProvider,
        snb: SnbDataProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.yield_spread_agent     = YieldSpreadAgent(macro, ecb, snb, bus)
        self.sovereign_spread_agent = SovereignSpreadAgent(ecb, bus)

    async def run(self) -> YieldCurveChiefResult:
        results = await asyncio.gather(
            self.yield_spread_agent.run(),
            self.sovereign_spread_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        yield_spreads     = _safe(results[0], YieldSpreadAgent.default())
        sovereign_spreads = _safe(results[1], SovereignSpreadAgent.default())

        self.bus.publish(YieldCurveChiefReady(source="yield_curve_chief_agent", payload={}))

        return YieldCurveChiefResult(
            yield_spreads=yield_spreads,
            sovereign_spreads=sovereign_spreads,
        )

    @staticmethod
    def default() -> YieldCurveChiefResult:
        return YieldCurveChiefResult(
            yield_spreads=YieldSpreadAgent.default(),
            sovereign_spreads=SovereignSpreadAgent.default(),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -k "yield_curve_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/market_cockpit/yield_curve_chief_agent.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add YieldCurveChiefAgent"
```

---

## Task 6: SectorChiefAgent

**Files:**
- Create: `agents/market_cockpit/sector_chief_agent.py`
- Test: `tests/test_chief_agents_cockpit.py`

Note: `SectorRotationAgent.run()` is **synchronous** and requires `regime` as parameter. `SectorChiefAgent.run(regime)` takes regime from `MacroChiefResult.regime`.

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_cockpit.py`:

```python
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.models import SectorChiefResult, SectorPerformanceSnapshot, MarketRegime

def _neutral_sector_performance():
    return SectorPerformanceSnapshot(
        usa={}, eurozone={},
        leading_usa="Technology", lagging_usa="Utilities",
        leading_eu="Technology", lagging_eu="Utilities",
    )

def test_sector_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = SectorChiefAgent(market, bus)
    chief.sector_performance_agent.run = AsyncMock(return_value=_neutral_sector_performance())

    result = asyncio.run(chief.run(MarketRegime.EXPANSION))
    assert isinstance(result, SectorChiefResult)
    bus.publish.assert_called_once()


def test_sector_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = SectorChiefAgent(market, bus)
    chief.sector_performance_agent.run = AsyncMock(side_effect=RuntimeError("down"))

    result = asyncio.run(chief.run(MarketRegime.EXPANSION))
    assert isinstance(result, SectorChiefResult)


def test_sector_chief_default():
    result = SectorChiefAgent.default()
    assert isinstance(result, SectorChiefResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_cockpit.py::test_sector_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/market_cockpit/sector_chief_agent.py`**

```python
import asyncio

from agents.market_cockpit.sector.sector_performance_agent import SectorPerformanceAgent
from agents.market_cockpit.sector.sector_rotation_agent import SectorRotationAgent
from core.domain.events import SectorChiefReady
from core.domain.models import MarketRegime, SectorChiefResult, SectorRotationSnapshot, Signal
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus

_DEFAULT_ROTATION = SectorRotationSnapshot(recommended=[], avoid=[], alignment="neutral", signal=Signal.NEUTRAL)


class SectorChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.sector_performance_agent = SectorPerformanceAgent(market, bus)
        self.sector_rotation_agent    = SectorRotationAgent(bus)

    async def run(self, regime: MarketRegime) -> SectorChiefResult:
        performance_result = await asyncio.gather(
            self.sector_performance_agent.run(),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        performance = _safe(performance_result[0], SectorPerformanceAgent.default())

        try:
            rotation = self.sector_rotation_agent.run(regime, performance.leading_usa)
        except Exception:
            rotation = SectorRotationAgent.default()

        self.bus.publish(SectorChiefReady(source="sector_chief_agent", payload={"regime": regime.value}))

        return SectorChiefResult(performance=performance, rotation=rotation)

    @staticmethod
    def default() -> SectorChiefResult:
        return SectorChiefResult(
            performance=SectorPerformanceAgent.default(),
            rotation=_DEFAULT_ROTATION,
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_cockpit.py -k "sector_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Run full cockpit test suite**

```
pytest tests/test_chief_agents_cockpit.py -v
# Expected: all passed
```

- [ ] **Step 6: Commit**

```bash
git add agents/market_cockpit/sector_chief_agent.py tests/test_chief_agents_cockpit.py
git commit -m "feat: add SectorChiefAgent"
```

---

## Task 7: Refactor TopDownOrchestrator

**Files:**
- Modify: `orchestrators/top_down_orchestrator.py`

- [ ] **Step 1: Replace contents of `orchestrators/top_down_orchestrator.py`**

```python
import asyncio

from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent import CommodityChiefAgent
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from core.domain.models import CockpitResult
from core.ports.data_provider import EcbDataProvider, MacroDataProvider, MarketDataProvider, SnbDataProvider
from core.ports.event_bus import EventBus


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
    ):
        self.macro_chief       = MacroChiefAgent(macro, ecb, snb, market, bus)
        self.commodity_chief   = CommodityChiefAgent(market, bus)
        self.sentiment_chief   = SentimentChiefAgent(market, bus)
        self.yield_curve_chief = YieldCurveChiefAgent(macro, ecb, snb, bus)
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
        commodities = _safe(commodities, CommodityChiefAgent.default())
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
```

- [ ] **Step 2: Run existing tests to verify no regressions**

```
pytest tests/ -v
# Expected: all previously passing tests still pass
```

- [ ] **Step 3: Commit**

```bash
git add orchestrators/top_down_orchestrator.py
git commit -m "refactor: TopDownOrchestrator uses 5 ChiefAgents"
```

---

## Task 8: EquityChiefAgent

**Files:**
- Create: `agents/stock_deep_dive/equity_chief_agent.py`
- Test: `tests/test_chief_agents_deep_dive.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_chief_agents_deep_dive.py
import asyncio
from unittest.mock import MagicMock, AsyncMock
from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from core.domain.models import (
    EquityChiefResult, Signal,
    FundamentalsSnapshot, QualitySnapshot, ShortInterestSnapshot,
    InsiderSnapshot, EarningsTrendSnapshot, MoatSnapshot, MoatScore,
    ValuationRangeSnapshot,
)

def _neutral_fundamentals():
    return FundamentalsSnapshot(
        pe_ratio=None, forward_pe=None, shiller_cape=None, peg_ratio=None,
        ev_ebitda=None, ev_revenue=None, price_book=None, price_sales=None,
        price_fcf=None, dividend_yield=None, wacc=None,
        revenue_cagr_3y=None, operating_margin=None, gross_margin=None,
        debt_to_equity=None, signal=Signal.NEUTRAL,
    )

def _neutral_quality():
    return QualitySnapshot(
        gross_margin=None, operating_margin=None, net_margin=None,
        fcf_margin=None, roe=None, roa=None, roic=None,
        debt_to_equity=None, net_debt_ebitda=None, interest_coverage=None,
        current_ratio=None, altman_z=None, signal=Signal.NEUTRAL,
    )

def _neutral_moat():
    s = MoatScore(score=0, evidence="")
    return MoatSnapshot(
        intangible_assets=s, switching_costs=s, network_effects=s,
        cost_advantages=s, efficient_scale=s,
        total_score=0, overall="none", llm_reasoning="", signal=Signal.NEUTRAL,
    )

def _neutral_valuation_range():
    return ValuationRangeSnapshot(
        methods=[], combined_low=0.0, combined_high=0.0,
        current_price=None, position="unknown", signal=Signal.NEUTRAL,
    )


def test_equity_chief_returns_result():
    bus = MagicMock()
    fundamentals = MagicMock()
    market = MagicMock()
    llm = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)
    chief.fundamentals_agent.run    = AsyncMock(return_value=_neutral_fundamentals())
    chief.quality_agent.run         = AsyncMock(return_value=_neutral_quality())
    chief.short_agent.run           = AsyncMock(return_value=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL))
    chief.insider_agent.run         = AsyncMock(return_value=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL))
    chief.earnings_agent.run        = AsyncMock(return_value=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL))
    chief.moat_agent.run            = AsyncMock(return_value=_neutral_moat())
    chief.valuation_range_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("AAPL", "technology"))
    assert isinstance(result, EquityChiefResult)
    bus.publish.assert_called_once()


def test_equity_chief_resilience():
    bus = MagicMock()
    fundamentals = MagicMock()
    market = MagicMock()
    llm = MagicMock()
    chief = EquityChiefAgent(fundamentals, market, llm, bus)
    chief.fundamentals_agent.run    = AsyncMock(side_effect=RuntimeError("API down"))
    chief.quality_agent.run         = AsyncMock(return_value=_neutral_quality())
    chief.short_agent.run           = AsyncMock(return_value=ShortInterestSnapshot(short_float_pct=None, days_to_cover=None, signal=Signal.NEUTRAL))
    chief.insider_agent.run         = AsyncMock(return_value=InsiderSnapshot(net_direction="unknown", recent_transactions=0, signal=Signal.NEUTRAL))
    chief.earnings_agent.run        = AsyncMock(return_value=EarningsTrendSnapshot(beat_rate=None, estimate_revision="stable", signal=Signal.NEUTRAL))
    chief.moat_agent.run            = AsyncMock(return_value=_neutral_moat())
    chief.valuation_range_agent.run = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("AAPL", "technology"))
    assert isinstance(result, EquityChiefResult)


def test_equity_chief_default():
    result = EquityChiefAgent.default()
    assert isinstance(result, EquityChiefResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_deep_dive.py::test_equity_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/stock_deep_dive/equity_chief_agent.py`**

```python
import asyncio

from agents.stock_deep_dive.equity.fundamentals_agent import FundamentalsAgent
from agents.stock_deep_dive.equity.quality_agent import QualityAgent
from agents.stock_deep_dive.equity.short_interest_agent import ShortInterestAgent
from agents.stock_deep_dive.equity.insider_agent import InsiderAgent
from agents.stock_deep_dive.equity.earnings_trend_agent import EarningsTrendAgent
from agents.stock_deep_dive.equity.moat_agent import MoatAgent
from agents.stock_deep_dive.equity.valuation_range_agent import ValuationRangeAgent
from core.domain.events import EquityChiefReady
from core.domain.models import EquityChiefResult
from core.ports.data_provider import FundamentalsProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


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

    async def run(self, ticker: str, sector: str = "default") -> EquityChiefResult:
        results = await asyncio.gather(
            self.fundamentals_agent.run(ticker),
            self.quality_agent.run(ticker),
            self.short_agent.run(ticker),
            self.insider_agent.run(ticker),
            self.earnings_agent.run(ticker),
            self.moat_agent.run(ticker),
            self.valuation_range_agent.run(ticker, sector),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        fundamentals    = _safe(results[0], FundamentalsAgent.default())
        quality         = _safe(results[1], QualityAgent.default())
        short_interest  = _safe(results[2], ShortInterestAgent.default())
        insider         = _safe(results[3], InsiderAgent.default())
        earnings_trend  = _safe(results[4], EarningsTrendAgent.default())
        moat            = _safe(results[5], MoatAgent.default())
        valuation_range = _safe(results[6], ValuationRangeAgent.default())

        self.bus.publish(EquityChiefReady(source="equity_chief_agent", payload={"ticker": ticker}))

        return EquityChiefResult(
            fundamentals=fundamentals,
            quality=quality,
            short_interest=short_interest,
            insider=insider,
            earnings_trend=earnings_trend,
            moat=moat,
            valuation_range=valuation_range,
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
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_deep_dive.py -k "equity_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/equity_chief_agent.py tests/test_chief_agents_deep_dive.py
git commit -m "feat: add EquityChiefAgent"
```

---

## Task 9: BondChiefAgent

**Files:**
- Create: `agents/stock_deep_dive/bond_chief_agent.py`
- Test: `tests/test_chief_agents_deep_dive.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_deep_dive.py`:

```python
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from core.domain.models import (
    BondResult, BondMetricsSnapshot, BondDurationSnapshot,
    BondCreditSnapshot, BondSpreadSnapshot,
)

def _neutral_bond_metrics():
    return BondMetricsSnapshot(
        bond_type="government", current_price=None, coupon=None,
        maturity_years=None, ytm=None, ytc=None, current_yield=None,
        real_yield=None, country=None, breakeven_inflation=None,
        issuer=None, sector=None, signal=Signal.NEUTRAL,
    )

def _neutral_bond_duration():
    return BondDurationSnapshot(macaulay_duration=None, modified_duration=None, convexity=None, dv01=None, signal=Signal.NEUTRAL)

def _neutral_bond_credit():
    return BondCreditSnapshot(moodys=None, sp=None, fitch=None, category="investment_grade", trend="stable", default_probability=None, signal=Signal.NEUTRAL)

def _neutral_bond_spread():
    return BondSpreadSnapshot(spread_bps=None, oas=None, z_spread=None, spread_trend="stable", signal=Signal.NEUTRAL)


def test_bond_chief_returns_result():
    bus = MagicMock()
    fundamentals = MagicMock()
    macro = MagicMock()
    chief = BondChiefAgent(fundamentals, macro, bus)
    chief.bond_metrics_agent.run   = AsyncMock(return_value=_neutral_bond_metrics())
    chief.bond_duration_agent.run  = AsyncMock(return_value=_neutral_bond_duration())
    chief.bond_credit_agent.run    = AsyncMock(return_value=_neutral_bond_credit())
    chief.bond_spread_agent.run    = AsyncMock(return_value=_neutral_bond_spread())

    result = asyncio.run(chief.run("US10Y", "government", "stable"))
    assert isinstance(result, BondResult)
    bus.publish.assert_called_once()


def test_bond_chief_resilience():
    bus = MagicMock()
    fundamentals = MagicMock()
    macro = MagicMock()
    chief = BondChiefAgent(fundamentals, macro, bus)
    chief.bond_metrics_agent.run   = AsyncMock(side_effect=RuntimeError("down"))
    chief.bond_duration_agent.run  = AsyncMock(return_value=_neutral_bond_duration())
    chief.bond_credit_agent.run    = AsyncMock(return_value=_neutral_bond_credit())
    chief.bond_spread_agent.run    = AsyncMock(return_value=_neutral_bond_spread())

    result = asyncio.run(chief.run("US10Y", "government", "stable"))
    assert isinstance(result, BondResult)


def test_bond_chief_default():
    result = BondChiefAgent.default("US10Y", "government")
    assert isinstance(result, BondResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_deep_dive.py::test_bond_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/stock_deep_dive/bond_chief_agent.py`**

```python
import asyncio

from agents.stock_deep_dive.bond.bond_metrics_agent import BondMetricsAgent
from agents.stock_deep_dive.bond.bond_duration_agent import BondDurationAgent
from agents.stock_deep_dive.bond.bond_credit_agent import BondCreditAgent
from agents.stock_deep_dive.bond.bond_spread_agent import BondSpreadAgent
from core.domain.events import BondChiefReady
from core.domain.models import BondResult
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider
from core.ports.event_bus import EventBus


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

    async def run(self, ticker: str, bond_type: str, rate_direction: str) -> BondResult:
        results = await asyncio.gather(
            self.bond_metrics_agent.run(ticker, bond_type),
            self.bond_duration_agent.run(ticker, rate_direction),
            self.bond_credit_agent.run(ticker),
            self.bond_spread_agent.run(ticker),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        metrics  = _safe(results[0], BondMetricsAgent.default())
        duration = _safe(results[1], BondDurationAgent.default())
        credit   = _safe(results[2], BondCreditAgent.default())
        spread   = _safe(results[3], BondSpreadAgent.default())

        self.bus.publish(BondChiefReady(source="bond_chief_agent", payload={"ticker": ticker}))

        return BondResult(ticker=ticker, bond_type=bond_type, metrics=metrics, duration=duration, credit=credit, spread=spread)

    @staticmethod
    def default(ticker: str = "", bond_type: str = "government") -> BondResult:
        return BondResult(
            ticker=ticker, bond_type=bond_type,
            metrics=BondMetricsAgent.default(),
            duration=BondDurationAgent.default(),
            credit=BondCreditAgent.default(),
            spread=BondSpreadAgent.default(),
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_deep_dive.py -k "bond_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/bond_chief_agent.py tests/test_chief_agents_deep_dive.py
git commit -m "feat: add BondChiefAgent"
```

---

## Task 10: IndexChiefAgent

**Files:**
- Create: `agents/stock_deep_dive/index_chief_agent.py`
- Test: `tests/test_chief_agents_deep_dive.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_deep_dive.py`:

```python
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from core.domain.models import (
    IndexResult, IndexPriceSnapshot, IndexValuationSnapshot, IndexEarningsSnapshot,
    IndexBreadthSnapshot, IndexMomentumSnapshot, SectorCompositionSnapshot, IndexValuationRangeSnapshot,
)

def _neutral_index_price():
    return IndexPriceSnapshot(current_price=None, perf_1w=None, perf_1m=None, perf_3m=None, perf_ytd=None, perf_1y=None, perf_3y=None, perf_5y=None, high_52w=None, low_52w=None, signal=Signal.NEUTRAL)

def _neutral_index_valuation():
    return IndexValuationSnapshot(pe_trailing=None, pe_forward=None, shiller_cape=None, dividend_yield=None, ev_ebitda=None, signal=Signal.NEUTRAL)

def _neutral_index_earnings():
    return IndexEarningsSnapshot(eps_growth_1y=None, revenue_growth_1y=None, operating_margin=None, estimate_revision="stable", signal=Signal.NEUTRAL)

def _neutral_index_breadth():
    return IndexBreadthSnapshot(pct_above_ma50=None, pct_above_ma200=None, advance_decline_ratio=None, new_highs=None, new_lows=None, signal=Signal.NEUTRAL)

def _neutral_index_momentum():
    return IndexMomentumSnapshot(rsi_14=None, ma50=None, ma200=None, golden_cross=None, relative_strength=None, signal=Signal.NEUTRAL)

def _neutral_sector_composition():
    return SectorCompositionSnapshot(top_sector=None, top_sector_weight=None, top_holding=None, top_holding_weight=None, top_10_concentration=None, signal=Signal.NEUTRAL)

def _neutral_index_valuation_range():
    return IndexValuationRangeSnapshot(eps_estimate=None, pe_historical_low=None, pe_historical_high=None, price_low=None, price_mid=None, price_high=None, current_price=None, position="fair", signal=Signal.NEUTRAL)


def test_index_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = IndexChiefAgent(market, bus)
    chief.index_price_agent.run           = AsyncMock(return_value=_neutral_index_price())
    chief.index_valuation_agent.run       = AsyncMock(return_value=_neutral_index_valuation())
    chief.index_earnings_agent.run        = AsyncMock(return_value=_neutral_index_earnings())
    chief.index_breadth_agent.run         = AsyncMock(return_value=_neutral_index_breadth())
    chief.index_momentum_agent.run        = AsyncMock(return_value=_neutral_index_momentum())
    chief.sector_composition_agent.run    = AsyncMock(return_value=_neutral_sector_composition())
    chief.index_valuation_range_agent.run = AsyncMock(return_value=_neutral_index_valuation_range())

    result = asyncio.run(chief.run("SPY"))
    assert isinstance(result, IndexResult)
    bus.publish.assert_called_once()


def test_index_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = IndexChiefAgent(market, bus)
    chief.index_price_agent.run           = AsyncMock(side_effect=RuntimeError("down"))
    chief.index_valuation_agent.run       = AsyncMock(return_value=_neutral_index_valuation())
    chief.index_earnings_agent.run        = AsyncMock(return_value=_neutral_index_earnings())
    chief.index_breadth_agent.run         = AsyncMock(return_value=_neutral_index_breadth())
    chief.index_momentum_agent.run        = AsyncMock(return_value=_neutral_index_momentum())
    chief.sector_composition_agent.run    = AsyncMock(return_value=_neutral_sector_composition())
    chief.index_valuation_range_agent.run = AsyncMock(return_value=_neutral_index_valuation_range())

    result = asyncio.run(chief.run("SPY"))
    assert isinstance(result, IndexResult)


def test_index_chief_default():
    result = IndexChiefAgent.default("SPY")
    assert isinstance(result, IndexResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_deep_dive.py::test_index_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/stock_deep_dive/index_chief_agent.py`**

```python
import asyncio

from agents.stock_deep_dive.index.index_price_agent import IndexPriceAgent
from agents.stock_deep_dive.index.index_valuation_agent import IndexValuationAgent
from agents.stock_deep_dive.index.index_earnings_agent import IndexEarningsAgent
from agents.stock_deep_dive.index.index_breadth_agent import IndexBreadthAgent
from agents.stock_deep_dive.index.index_momentum_agent import IndexMomentumAgent
from agents.stock_deep_dive.index.sector_composition_agent import SectorCompositionAgent
from agents.stock_deep_dive.index.index_valuation_range_agent import IndexValuationRangeAgent
from core.domain.events import IndexChiefReady
from core.domain.models import IndexResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


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

        self.bus.publish(IndexChiefReady(source="index_chief_agent", payload={"ticker": ticker}))

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
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_deep_dive.py -k "index_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/index_chief_agent.py tests/test_chief_agents_deep_dive.py
git commit -m "feat: add IndexChiefAgent"
```

---

## Task 11: CommodityChiefAgent (Stock Deep Dive)

**Files:**
- Create: `agents/stock_deep_dive/commodity_chief_agent.py`
- Test: `tests/test_chief_agents_deep_dive.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_deep_dive.py`:

```python
from agents.stock_deep_dive.commodity_chief_agent import CommodityChiefAgent as CommodityDeepDiveChiefAgent
from core.domain.models import (
    CommodityBottomUpResult, SupplyDemandSnapshot, SeasonalitySnapshot,
    COTSnapshot, CommodityValuationRangeSnapshot,
)

def _neutral_supply_demand():
    return SupplyDemandSnapshot(inventory_current=None, inventory_avg_5y=None, inventory_pct_vs_avg=None, production_change_yoy=None, stock_to_flow=None, stock_to_flow_signal=None, signal=Signal.NEUTRAL)

def _neutral_seasonality():
    return SeasonalitySnapshot(current_month_bias="neutral", avg_return_this_month=None, positive_years_pct=None, signal=Signal.NEUTRAL)

def _neutral_cot():
    return COTSnapshot(net_speculative_long=None, net_speculative_pct_oi=None, signal=Signal.NEUTRAL)

def _neutral_commodity_valuation():
    return CommodityValuationRangeSnapshot(current_price=None, price_low_5y=None, price_high_5y=None, percentile_5y=None, percentile_10y=None, production_cost_low=None, production_cost_high=None, position="fair", signal=Signal.NEUTRAL)


def test_commodity_deep_dive_chief_returns_result():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityDeepDiveChiefAgent(market, bus)
    chief.supply_demand_agent.run          = AsyncMock(return_value=_neutral_supply_demand())
    chief.seasonality_agent.run            = AsyncMock(return_value=_neutral_seasonality())
    chief.cot_agent.run                    = AsyncMock(return_value=_neutral_cot())
    chief.commodity_valuation_range_agent.run = AsyncMock(return_value=_neutral_commodity_valuation())

    result = asyncio.run(chief.run("CL=F"))
    assert isinstance(result, CommodityBottomUpResult)
    bus.publish.assert_called_once()


def test_commodity_deep_dive_chief_resilience():
    bus = MagicMock()
    market = MagicMock()
    chief = CommodityDeepDiveChiefAgent(market, bus)
    chief.supply_demand_agent.run          = AsyncMock(side_effect=RuntimeError("down"))
    chief.seasonality_agent.run            = AsyncMock(return_value=_neutral_seasonality())
    chief.cot_agent.run                    = AsyncMock(return_value=_neutral_cot())
    chief.commodity_valuation_range_agent.run = AsyncMock(return_value=_neutral_commodity_valuation())

    result = asyncio.run(chief.run("CL=F"))
    assert isinstance(result, CommodityBottomUpResult)


def test_commodity_deep_dive_chief_default():
    result = CommodityDeepDiveChiefAgent.default("CL=F")
    assert isinstance(result, CommodityBottomUpResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_deep_dive.py::test_commodity_deep_dive_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/stock_deep_dive/commodity_chief_agent.py`**

```python
import asyncio

from agents.stock_deep_dive.commodity.supply_demand_agent import SupplyDemandAgent
from agents.stock_deep_dive.commodity.seasonality_agent import SeasonalityAgent
from agents.stock_deep_dive.commodity.cot_agent import COTAgent
from agents.stock_deep_dive.commodity.commodity_valuation_range_agent import CommodityValuationRangeAgent
from core.domain.events import CommodityBottomUpChiefReady
from core.domain.models import CommodityBottomUpResult
from core.ports.data_provider import MarketDataProvider
from core.ports.event_bus import EventBus


class CommodityChiefAgent:
    def __init__(self, market: MarketDataProvider, bus: EventBus):
        self.bus = bus
        self.supply_demand_agent          = SupplyDemandAgent(bus)
        self.seasonality_agent            = SeasonalityAgent(market, bus)
        self.cot_agent                    = COTAgent(bus)
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

        self.bus.publish(CommodityBottomUpChiefReady(source="commodity_chief_agent", payload={"ticker": ticker}))

        return CommodityBottomUpResult(
            commodity=ticker,
            supply_demand=supply_demand,
            seasonality=seasonality,
            cot=cot,
            valuation_range=valuation_range,
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
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_deep_dive.py -k "commodity_deep_dive_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/commodity_chief_agent.py tests/test_chief_agents_deep_dive.py
git commit -m "feat: add CommodityChiefAgent (stock deep dive)"
```

---

## Task 12: PreciousMetalsChiefAgent

**Files:**
- Create: `agents/stock_deep_dive/precious_metals_chief_agent.py`
- Test: `tests/test_chief_agents_deep_dive.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_deep_dive.py`:

```python
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import PreciousMetalsResult, PreciousMetalSnapshot, CrossMetalSnapshot, Signal

def _neutral_pm_price(metal="GOLD"):
    return PreciousMetalSnapshot(metal=metal, price_usd=None, performance={}, rsi=None, ma50=None, ma200=None, stock_to_flow=None, real_yield_correlation=None, signal=Signal.NEUTRAL)

def _neutral_cross_metal():
    return CrossMetalSnapshot(gold_silver_ratio=None, gold_platinum_ratio=None, signal=Signal.NEUTRAL)


def test_precious_metals_chief_returns_result():
    bus = MagicMock()
    macro = MagicMock()
    market = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    chief.pm_price_agent.run      = AsyncMock(return_value=_neutral_pm_price())
    chief.pm_cross_agent.run      = AsyncMock(return_value=_neutral_cross_metal())
    chief.pm_valuation_agent.run  = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("GOLD"))
    assert isinstance(result, PreciousMetalsResult)
    bus.publish.assert_called_once()


def test_precious_metals_chief_resilience():
    bus = MagicMock()
    macro = MagicMock()
    market = MagicMock()
    chief = PreciousMetalsChiefAgent(macro, market, bus)
    chief.pm_price_agent.run      = AsyncMock(side_effect=RuntimeError("down"))
    chief.pm_cross_agent.run      = AsyncMock(return_value=_neutral_cross_metal())
    chief.pm_valuation_agent.run  = AsyncMock(return_value=_neutral_valuation_range())

    result = asyncio.run(chief.run("GOLD"))
    assert isinstance(result, PreciousMetalsResult)


def test_precious_metals_chief_default():
    result = PreciousMetalsChiefAgent.default("GOLD")
    assert isinstance(result, PreciousMetalsResult)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_deep_dive.py::test_precious_metals_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/stock_deep_dive/precious_metals_chief_agent.py`**

```python
import asyncio

from agents.stock_deep_dive.precious_metals.precious_metal_price_agent import PreciousMetalPriceAgent
from agents.stock_deep_dive.precious_metals.cross_metal_agent import CrossMetalAgent
from agents.stock_deep_dive.precious_metals.precious_metals_valuation_agent import PreciousMetalsValuationAgent
from core.domain.events import PreciousMetalsChiefReady
from core.domain.models import PreciousMetalsResult, Signal
from core.ports.data_provider import MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus


class PreciousMetalsChiefAgent:
    def __init__(
        self,
        macro: MacroDataProvider,
        market: MarketDataProvider,
        bus: EventBus,
    ):
        self.bus = bus
        self.pm_price_agent     = PreciousMetalPriceAgent(market, bus)
        self.pm_cross_agent     = CrossMetalAgent(market, bus)
        self.pm_valuation_agent = PreciousMetalsValuationAgent(macro, market, bus)

    async def run(self, metal: str) -> PreciousMetalsResult:
        results = await asyncio.gather(
            self.pm_price_agent.run(metal),
            self.pm_cross_agent.run(),
            self.pm_valuation_agent.run(metal),
            return_exceptions=True,
        )

        def _safe(r, d): return d if isinstance(r, Exception) else r

        price_snap    = _safe(results[0], PreciousMetalPriceAgent.default(metal))
        cross_snap    = _safe(results[1], CrossMetalAgent.default())
        valuation_snap = _safe(results[2], PreciousMetalsValuationAgent.default())

        self.bus.publish(PreciousMetalsChiefReady(source="precious_metals_chief_agent", payload={"metal": metal}))

        return PreciousMetalsResult(
            metal=metal,
            price_analysis=price_snap,
            cross_metal=cross_snap,
            valuation_range=valuation_snap,
            cot_signal=Signal.NEUTRAL,
            currency_impact={},
        )

    @staticmethod
    def default(metal: str = "") -> PreciousMetalsResult:
        return PreciousMetalsResult(
            metal=metal,
            price_analysis=PreciousMetalPriceAgent.default(metal),
            cross_metal=CrossMetalAgent.default(),
            valuation_range=PreciousMetalsValuationAgent.default(),
            cot_signal=Signal.NEUTRAL,
            currency_impact={},
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_deep_dive.py -k "precious_metals_chief" -v
# Expected: 3 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/stock_deep_dive/precious_metals_chief_agent.py tests/test_chief_agents_deep_dive.py
git commit -m "feat: add PreciousMetalsChiefAgent"
```

---

## Task 13: Refactor BottomUpOrchestrator

**Files:**
- Modify: `orchestrators/bottom_up_orchestrator.py`

- [ ] **Step 1: Replace contents of `orchestrators/bottom_up_orchestrator.py`**

```python
from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.commodity_chief_agent import CommodityChiefAgent
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from core.domain.models import BottomUpResult
from core.ports.data_provider import FundamentalsProvider, MacroDataProvider, MarketDataProvider
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class BottomUpOrchestrator:
    """
    Modus 2 — Bottom-Up Analyse.
    Verzweigt nach asset_class und delegiert an den zuständigen ChiefAgent.
    """

    def __init__(
        self,
        fundamentals_provider: FundamentalsProvider,
        macro_provider: MacroDataProvider,
        market_provider: MarketDataProvider,
        llm: LLMProvider,
        bus: EventBus,
    ):
        self.equity_chief          = EquityChiefAgent(fundamentals_provider, market_provider, llm, bus)
        self.bond_chief            = BondChiefAgent(fundamentals_provider, macro_provider, bus)
        self.index_chief           = IndexChiefAgent(market_provider, bus)
        self.commodity_chief       = CommodityChiefAgent(market_provider, bus)
        self.precious_metals_chief = PreciousMetalsChiefAgent(macro_provider, market_provider, bus)

    async def run(
        self,
        ticker: str,
        asset_class: str = "equity",
        sector: str = "default",
        bond_type: str = "government",
        rate_direction: str = "stable",
    ) -> BottomUpResult:
        if asset_class == "precious_metal":
            return await self._run_precious_metals(ticker)
        if asset_class == "bond":
            return await self._run_bond(ticker, bond_type, rate_direction)
        if asset_class == "index":
            return await self._run_index(ticker)
        if asset_class == "commodity":
            return await self._run_commodity(ticker)
        return await self._run_equity(ticker, asset_class, sector)

    async def _run_equity(self, ticker: str, asset_class: str, sector: str) -> BottomUpResult:
        try:
            result = await self.equity_chief.run(ticker, sector)
        except Exception:
            result = EquityChiefAgent.default()
        return BottomUpResult(
            ticker=ticker, asset_class=asset_class,
            fundamentals=result.fundamentals,
            quality=result.quality,
            short_interest=result.short_interest,
            insider=result.insider,
            earnings_trend=result.earnings_trend,
            moat=result.moat,
            valuation_range=result.valuation_range,
            precious_metals=None, bond=None, index=None, commodity_deep=None,
        )

    async def _run_bond(self, ticker: str, bond_type: str, rate_direction: str) -> BottomUpResult:
        try:
            bond_result = await self.bond_chief.run(ticker, bond_type, rate_direction)
        except Exception:
            bond_result = BondChiefAgent.default(ticker, bond_type)
        return BottomUpResult(
            ticker=ticker, asset_class="bond",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=bond_result, index=None, commodity_deep=None,
        )

    async def _run_index(self, ticker: str) -> BottomUpResult:
        try:
            index_result = await self.index_chief.run(ticker)
        except Exception:
            index_result = IndexChiefAgent.default(ticker)
        return BottomUpResult(
            ticker=ticker, asset_class="index",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=index_result, commodity_deep=None,
        )

    async def _run_commodity(self, ticker: str) -> BottomUpResult:
        try:
            commodity_result = await self.commodity_chief.run(ticker)
        except Exception:
            commodity_result = CommodityChiefAgent.default(ticker)
        return BottomUpResult(
            ticker=ticker, asset_class="commodity",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None, valuation_range=None,
            precious_metals=None, bond=None, index=None, commodity_deep=commodity_result,
        )

    async def _run_precious_metals(self, metal: str) -> BottomUpResult:
        try:
            pm_result = await self.precious_metals_chief.run(metal)
        except Exception:
            pm_result = PreciousMetalsChiefAgent.default(metal)
        return BottomUpResult(
            ticker=metal, asset_class="precious_metal",
            fundamentals=None, quality=None, short_interest=None,
            insider=None, earnings_trend=None, moat=None,
            valuation_range=pm_result.valuation_range,
            precious_metals=pm_result, bond=None, index=None, commodity_deep=None,
        )
```

- [ ] **Step 2: Run full test suite — verify no regressions**

```
pytest tests/ -v
# Expected: all previously passing tests still pass
```

- [ ] **Step 3: Commit**

```bash
git add orchestrators/bottom_up_orchestrator.py
git commit -m "refactor: BottomUpOrchestrator uses 5 ChiefAgents"
```

---

## Task 14: AnomalyChiefAgent

**Files:**
- Create: `agents/anomaly_chief_agent.py`
- Test: `tests/test_chief_agents_judgment.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_chief_agents_judgment.py
from unittest.mock import MagicMock
from agents.anomaly_chief_agent import AnomalyChiefAgent
from core.domain.models import AnomalyReport


def _empty_report():
    return AnomalyReport.empty()

def _make_cockpit():
    cockpit = MagicMock()
    cockpit.sentiment.vix.vix = 18.0
    cockpit.sentiment.vix.signal = MagicMock()
    cockpit.sentiment.fear_greed.value = 50.0
    cockpit.sentiment.fear_greed.signal = MagicMock()
    cockpit.sentiment.put_call.signal = MagicMock()
    cockpit.yield_curve.yield_spreads.usa.spread_10y2y = 1.0
    cockpit.yield_curve.yield_spreads.usa.signal = MagicMock()
    cockpit.macro.regime_confidence = 0.75
    cockpit.macro.inflation.usa.cpi = 3.0
    cockpit.macro.inflation.usa.signal = MagicMock()
    cockpit.macro.gdp.usa.signal = MagicMock()
    cockpit.commodities.energy.signal = MagicMock()
    cockpit.commodities.industrial_metals.signal = MagicMock()
    return cockpit

def _make_bottom_up():
    bu = MagicMock()
    bu.asset_class = "equity"
    bu.fundamentals = None
    bu.short_interest = None
    bu.insider = None
    bu.earnings_trend.signal = MagicMock()
    bu.moat.signal = MagicMock()
    bu.valuation_range.signal = MagicMock()
    bu.quality.signal = MagicMock()
    return bu


def test_anomaly_chief_returns_two_reports():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    td, bu = chief.run(_make_cockpit(), _make_bottom_up(), [], [])
    assert isinstance(td, AnomalyReport)
    assert isinstance(bu, AnomalyReport)
    bus.publish.assert_called_once()


def test_anomaly_chief_no_cockpit():
    bus = MagicMock()
    chief = AnomalyChiefAgent(bus)
    td, bu = chief.run(None, _make_bottom_up(), [], [])
    assert td.has_anomalies is False
    assert isinstance(bu, AnomalyReport)
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_judgment.py::test_anomaly_chief_returns_two_reports -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/anomaly_chief_agent.py`**

```python
from agents.anomaly.top_down_anomaly_agent import TopDownAnomalyAgent
from agents.anomaly.bottom_up_anomaly_agent import BottomUpAnomalyAgent
from core.domain.events import AnomalyChiefReady
from core.domain.models import AnomalyReport
from core.ports.event_bus import EventBus


class AnomalyChiefAgent:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.td_anomaly_agent = TopDownAnomalyAgent()
        self.bu_anomaly_agent = BottomUpAnomalyAgent()

    def run(
        self,
        cockpit,
        bottom_up,
        ticker_history: list[dict],
        global_history: list[dict],
    ) -> tuple[AnomalyReport, AnomalyReport]:
        td_anomaly = (
            self.td_anomaly_agent.run(cockpit, global_history)
            if cockpit is not None
            else AnomalyReport.empty()
        )
        try:
            bu_anomaly = self.bu_anomaly_agent.run(bottom_up, ticker_history)
        except Exception:
            bu_anomaly = AnomalyReport.empty()

        self.bus.publish(AnomalyChiefReady(source="anomaly_chief_agent", payload={
            "td_severity": td_anomaly.severity,
            "bu_severity": bu_anomaly.severity,
        }))

        return td_anomaly, bu_anomaly
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_judgment.py -k "anomaly_chief" -v
# Expected: 2 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/anomaly_chief_agent.py tests/test_chief_agents_judgment.py
git commit -m "feat: add AnomalyChiefAgent"
```

---

## Task 15: JudgmentChiefAgent

**Files:**
- Create: `agents/judgment_chief_agent.py`
- Test: `tests/test_chief_agents_judgment.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_judgment.py`:

```python
import asyncio
from unittest.mock import AsyncMock
from agents.judgment_chief_agent import JudgmentChiefAgent
from core.domain.models import DeepDiveResult, Recommendation, InvestmentRecommendation, AnomalyReport, Signal


def _make_deep_dive_result():
    return DeepDiveResult(
        ticker="AAPL", asset_class="equity", market="USA",
        top_down_context="neutral", top_down_available=True,
        judgment="Hold", alignment="mixed",
        recommendation=InvestmentRecommendation(
            action=Recommendation.HOLD, short_type=None, short_warning=None,
            confidence=0.65, reasoning="neutral",
        ),
        dominant_signal="neutral", confidence=0.65, xai_explanation="",
    )


def test_judgment_chief_returns_result():
    bus = MagicMock()
    llm = MagicMock()
    bottom_up = MagicMock()
    bottom_up.ticker = "AAPL"
    bottom_up.asset_class = "equity"

    chief = JudgmentChiefAgent(llm, bus)
    chief.judgment_agent.run = AsyncMock(return_value=_make_deep_dive_result())

    result = asyncio.run(chief.run(
        ticker="AAPL",
        top_down_context="neutral macro",
        bottom_up=bottom_up,
        cockpit=None,
        market="USA",
        in_portfolio=False,
        top_down_available=False,
        top_down_anomaly=AnomalyReport.empty(),
        bottom_up_anomaly=AnomalyReport.empty(),
        backtester_context={},
    ))
    assert isinstance(result, DeepDiveResult)
    bus.publish.assert_called_once()
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_judgment.py::test_judgment_chief_returns_result -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/judgment_chief_agent.py`**

```python
from agents.judgment.judgment_agent import JudgmentAgent
from core.domain.events import JudgmentChiefReady
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider


class JudgmentChiefAgent:
    def __init__(self, llm: LLMProvider, bus: EventBus):
        self.bus = bus
        self.judgment_agent = JudgmentAgent(llm, bus)

    async def run(
        self,
        ticker: str,
        top_down_context: str,
        bottom_up: BottomUpResult,
        cockpit: CockpitResult,
        market: str,
        in_portfolio: bool,
        top_down_available: bool,
        top_down_anomaly: AnomalyReport,
        bottom_up_anomaly: AnomalyReport,
        backtester_context: dict,
    ) -> DeepDiveResult:
        result = await self.judgment_agent.run(
            ticker=ticker,
            top_down_context=top_down_context,
            bottom_up=bottom_up,
            cockpit=cockpit,
            market=market,
            in_portfolio=in_portfolio,
            top_down_available=top_down_available,
            top_down_anomaly=top_down_anomaly,
            bottom_up_anomaly=bottom_up_anomaly,
            backtester_context=backtester_context,
        )

        self.bus.publish(JudgmentChiefReady(source="judgment_chief_agent", payload={
            "ticker": ticker,
            "recommendation": result.recommendation.action.value,
            "confidence": result.confidence,
        }))

        return result
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_judgment.py -k "judgment_chief" -v
# Expected: 1 passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/judgment_chief_agent.py tests/test_chief_agents_judgment.py
git commit -m "feat: add JudgmentChiefAgent"
```

---

## Task 16: BacktesterChiefAgent

**Files:**
- Create: `agents/backtester_chief_agent.py`
- Test: `tests/test_chief_agents_judgment.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_chief_agents_judgment.py`:

```python
from agents.backtester_chief_agent import BacktesterChiefAgent


def test_backtester_chief_load_context_empty():
    bus = MagicMock()
    memory = MagicMock()
    memory.load_latest_backtester_report = MagicMock(return_value={})
    chief = BacktesterChiefAgent(memory, bus)
    ctx = chief.load_context()
    assert isinstance(ctx, dict)


def test_backtester_chief_run_calls_all_agents():
    bus = MagicMock()
    memory = MagicMock()
    memory.load_global_history = MagicMock(return_value=[])
    chief = BacktesterChiefAgent(memory, bus)
    chief.td_backtester.run   = AsyncMock(return_value=None)
    chief.bu_backtester.run   = AsyncMock(return_value=None)
    chief.j_backtester.run    = AsyncMock(return_value=None)

    asyncio.run(chief.run())
    chief.td_backtester.run.assert_called_once()
    chief.bu_backtester.run.assert_called_once()
    chief.j_backtester.run.assert_called_once()
    bus.publish.assert_called_once()
```

- [ ] **Step 2: Run test — expect FAIL**

```
pytest tests/test_chief_agents_judgment.py::test_backtester_chief_load_context_empty -v
# Expected: ImportError
```

- [ ] **Step 3: Create `agents/backtester_chief_agent.py`**

```python
import asyncio

from agents.backtester.top_down_backtester_agent import TopDownBacktesterAgent
from agents.backtester.bottom_up_backtester_agent import BottomUpBacktesterAgent
from agents.backtester.judgment_backtester_agent import JudgmentBacktesterAgent
from core.domain.events import BacktesterChiefReady
from core.ports.event_bus import EventBus
from core.ports.memory_port import MemoryPort


class BacktesterChiefAgent:
    def __init__(self, memory: MemoryPort, bus: EventBus):
        self.memory = memory
        self.bus    = bus
        self.td_backtester = TopDownBacktesterAgent(memory)
        self.bu_backtester = BottomUpBacktesterAgent(memory)
        self.j_backtester  = JudgmentBacktesterAgent(memory)

    def load_context(self) -> dict:
        return self.memory.load_latest_backtester_report("judgment") or {}

    async def run(self) -> None:
        await asyncio.gather(
            self.td_backtester.run(),
            self.bu_backtester.run(),
            self.j_backtester.run(),
            return_exceptions=True,
        )
        self.bus.publish(BacktesterChiefReady(source="backtester_chief_agent", payload={}))
```

- [ ] **Step 4: Run tests — expect PASS**

```
pytest tests/test_chief_agents_judgment.py -v
# Expected: all passed
```

- [ ] **Step 5: Commit**

```bash
git add agents/backtester_chief_agent.py tests/test_chief_agents_judgment.py
git commit -m "feat: add BacktesterChiefAgent"
```

---

## Task 17: Refactor JudgmentOrchestrator

**Files:**
- Modify: `orchestrators/judgment_orchestrator.py`

- [ ] **Step 1: Replace contents of `orchestrators/judgment_orchestrator.py`**

```python
from agents.anomaly_chief_agent import AnomalyChiefAgent
from agents.judgment_chief_agent import JudgmentChiefAgent
from agents.backtester_chief_agent import BacktesterChiefAgent
from core.domain.models import AnomalyReport, BottomUpResult, CockpitResult, DeepDiveResult
from core.domain.top_down_context import derive_top_down_context
from core.ports.event_bus import EventBus
from core.ports.llm_provider import LLMProvider
from core.ports.memory_port import MemoryPort

FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}


class JudgmentOrchestrator:
    """
    Modus 3 — Kombinations-Urteil.
    Koordiniert 3 ChiefAgents: Anomalie-Erkennung, Urteil, Backtesting-Kontext.
    """

    def __init__(self, llm: LLMProvider, bus: EventBus, memory: MemoryPort):
        self.memory           = memory
        self.anomaly_chief    = AnomalyChiefAgent(bus)
        self.judgment_chief   = JudgmentChiefAgent(llm, bus)
        self.backtester_chief = BacktesterChiefAgent(memory, bus)

    async def run(
        self,
        cockpit: CockpitResult,
        bottom_up: BottomUpResult,
        market: str,
        in_portfolio: bool = False,
        sector: str = "default",
    ) -> DeepDiveResult:
        top_down_available = cockpit is not None and market in FULL_ANALYSIS_MARKETS
        top_down_context = (
            derive_top_down_context(cockpit, sector=sector)
            if top_down_available
            else f"Kein vollständiger Top-Down-Kontext verfügbar (Markt: {market})."
        )

        ticker_history = self.memory.load_history(bottom_up.ticker, days=90)
        global_history = self.memory.load_global_history(days=90)

        td_anomaly, bu_anomaly = self.anomaly_chief.run(
            cockpit, bottom_up, ticker_history, global_history
        )
        backtester_context = self.backtester_chief.load_context()

        result = await self.judgment_chief.run(
            ticker=bottom_up.ticker,
            top_down_context=top_down_context,
            bottom_up=bottom_up,
            cockpit=cockpit,
            market=market,
            in_portfolio=in_portfolio,
            top_down_available=top_down_available,
            top_down_anomaly=td_anomaly,
            bottom_up_anomaly=bu_anomaly,
            backtester_context=backtester_context,
        )

        self.memory.save_analysis(result, cockpit, price=None)
        return result
```

- [ ] **Step 2: Run full test suite**

```
pytest tests/ -v
# Expected: all tests pass
```

- [ ] **Step 3: Commit**

```bash
git add orchestrators/judgment_orchestrator.py
git commit -m "refactor: JudgmentOrchestrator uses 3 ChiefAgents"
```

---

## Final Verification

- [ ] **Run full test suite one last time**

```
pytest tests/ -v
# Expected: all tests pass, no regressions
```

- [ ] **Verify file structure**

```
python -c "
from agents.market_cockpit.macro_chief_agent import MacroChiefAgent
from agents.market_cockpit.commodity_chief_agent import CommodityChiefAgent
from agents.market_cockpit.sentiment_chief_agent import SentimentChiefAgent
from agents.market_cockpit.yield_curve_chief_agent import YieldCurveChiefAgent
from agents.market_cockpit.sector_chief_agent import SectorChiefAgent
from agents.stock_deep_dive.equity_chief_agent import EquityChiefAgent
from agents.stock_deep_dive.bond_chief_agent import BondChiefAgent
from agents.stock_deep_dive.index_chief_agent import IndexChiefAgent
from agents.stock_deep_dive.commodity_chief_agent import CommodityChiefAgent as CommodityBU
from agents.stock_deep_dive.precious_metals_chief_agent import PreciousMetalsChiefAgent
from agents.anomaly_chief_agent import AnomalyChiefAgent
from agents.judgment_chief_agent import JudgmentChiefAgent
from agents.backtester_chief_agent import BacktesterChiefAgent
print('All 13 ChiefAgents importable')
"
```
