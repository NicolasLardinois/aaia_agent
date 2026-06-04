# ChiefAgents Design

**Datum:** 2026-06-04
**Status:** Approved

## Kontext: Trigger-Flow

```
Geplant / Hintergrund (kein User-Input nötig):
  TopDownOrchestrator      → Dashboard-Refresh (permanent / geplant)
  BacktesterChiefAgent     → überprüft vergangene Urteile autonom, speichert Report in Memory

User sucht "AAPL":
  BottomUpOrchestrator     → frische Analyse für Ticker
  JudgmentOrchestrator     → Urteil (lädt Backtester-Report aus Memory zur Konfidenz-Kalibrierung)
```

Bottom-Up und aktives Judgment starten nie ohne expliziten Ticker. TopDown und Backtesting laufen unabhängig im Hintergrund.

## Ziel

Einführung einer ChiefAgent-Schicht zwischen Orchestratoren und Sub-Agents. Jeder ChiefAgent koordiniert eine Domain-Gruppe und kapselt deren Sub-Agents. Orchestratoren sprechen nur noch mit Chiefs, nicht mehr direkt mit Sub-Agents.

## Architektur

```
Orchestrator
    └── ChiefAgent      (Domain-Koordinator, NEU)
            └── SubAgent    (Specialist, unverändert)
```

## Ordnerstruktur

ChiefAgents liegen eine Ebene über ihren Sub-Agent-Ordnern (Option C — flach in der Bereichs-Ebene):

```
agents/
  market_cockpit/
    macro_chief_agent.py           ← NEU
    commodity_chief_agent.py       ← NEU
    sentiment_chief_agent.py       ← NEU
    yield_curve_chief_agent.py     ← NEU
    sector_chief_agent.py          ← NEU
    macro/        (Sub-Agents, unverändert)
    commodity/    (Sub-Agents, unverändert)
    sentiment/    (Sub-Agents, unverändert)
    yield_curve/  (Sub-Agents, unverändert)
    sector/       (Sub-Agents, unverändert)

  stock_deep_dive/
    equity_chief_agent.py          ← NEU
    bond_chief_agent.py            ← NEU
    index_chief_agent.py           ← NEU
    commodity_chief_agent.py       ← NEU
    precious_metals_chief_agent.py ← NEU
    equity/       (Sub-Agents, unverändert)
    bond/         (Sub-Agents, unverändert)
    index/        (Sub-Agents, unverändert)
    commodity/    (Sub-Agents, unverändert)
    precious_metals/ (Sub-Agents, unverändert)

  anomaly_chief_agent.py           ← NEU
  judgment_chief_agent.py          ← NEU
  backtester_chief_agent.py        ← NEU
  anomaly/      (Sub-Agents, unverändert)
  judgment/     (Sub-Agents, unverändert)
  backtester/   (Sub-Agents, unverändert)
```

## ChiefAgent-Muster

Jeder ChiefAgent folgt demselben Muster wie Sub-Agents:

```python
class MacroChiefAgent:
    def __init__(self, macro, ecb, snb, market, bus):
        # Sub-Agents instanziieren
        self.inflation_agent    = InflationAgent(macro, ecb, snb, bus)
        self.money_supply_agent = MoneySupplyAgent(macro, ecb, snb, bus)
        # ...
        self.bus = bus

    async def run(self) -> MacroChiefResult:
        results = await asyncio.gather(
            self.inflation_agent.run(), ...,
            return_exceptions=True
        )
        inflation = results[0] if not isinstance(results[0], Exception) else InflationAgent.default()
        # ...
        self.bus.publish(MacroChiefReady(source="macro_chief_agent", payload={}))
        return MacroChiefResult(inflation=inflation, ...)

    @staticmethod
    def default() -> MacroChiefResult:
        # Neutrale Fallback-Werte
        ...
```

## Resilience (zwei Ebenen)

**Ebene 1 — Sub-Agent fällt aus:**
- `asyncio.gather(..., return_exceptions=True)` im ChiefAgent
- Fallback auf `SubAgent.default()`
- Andere Sub-Agents laufen weiter

**Ebene 2 — ChiefAgent selbst fällt aus:**
- `asyncio.gather(..., return_exceptions=True)` im Orchestrator
- Fallback auf `ChiefAgent.default()`
- Andere ChiefAgents laufen weiter
- System liefert immer ein vollständiges Result-Objekt

Kein `is_fallback`-Flag.

## Neue Domain-Modelle (`models.py`)

`EquityChiefResult` wird hinzugefügt (fehlt als einzige Chief-Ebene):

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

Bestehende Chief-Result-Typen (werden von Chiefs zurückgegeben):
- `MacroChiefResult` → `MacroChiefAgent`
- `CommodityChiefResult` → `CommodityChiefAgent` (market cockpit)
- `SentimentChiefResult` → `SentimentChiefAgent`
- `YieldCurveChiefResult` → `YieldCurveChiefAgent`
- `SectorChiefResult` → `SectorChiefAgent`
- `EquityChiefResult` → `EquityChiefAgent` (NEU)
- `BondResult` → `BondChiefAgent`
- `IndexResult` → `IndexChiefAgent`
- `CommodityBottomUpResult` → `CommodityChiefAgent` (stock deep dive)
- `PreciousMetalsResult` → `PreciousMetalsChiefAgent`

## Neue Events (`events.py`)

```python
# Bereits vorhanden:
class MacroChiefReady(AgentEvent): pass

# NEU — Market Cockpit:
class CommodityChiefReady(AgentEvent): pass
class SentimentChiefReady(AgentEvent): pass
class YieldCurveChiefReady(AgentEvent): pass
class SectorChiefReady(AgentEvent): pass

# NEU — Stock Deep Dive:
class EquityChiefReady(AgentEvent): pass
class BondChiefReady(AgentEvent): pass
class IndexChiefReady(AgentEvent): pass
class CommodityBottomUpChiefReady(AgentEvent): pass
class PreciousMetalsChiefReady(AgentEvent): pass

# NEU — Judgment:
class AnomalyChiefReady(AgentEvent): pass
class JudgmentChiefReady(AgentEvent): pass
class BacktesterChiefReady(AgentEvent): pass
```

## Sonderfälle

**SectorChiefAgent:** `SectorRotationAgent.run()` braucht `regime` als Input (kommt aus dem Makro-Ergebnis). Deshalb:
- `MacroChiefAgent` läuft zuerst und gibt `MacroChiefResult` zurück (enthält bereits `regime`)
- `SectorChiefAgent.run(regime)` bekommt das Regime vom Orchestrator übergeben
- Alle anderen Chiefs laufen parallel zu MacroChief; SectorChief läuft danach

**BacktesterChiefAgent:** Backtester-Agents laufen eigenständig (getrennte Prozesse). `BacktesterChiefAgent` lädt deren Reports via `MemoryPort` und stellt Kontext für `JudgmentChiefAgent` bereit.

## Vereinfachte Orchestratoren

**TopDownOrchestrator** (17 Agents → 5 Chiefs):
```python
def __init__(self, macro, ecb, snb, market, bus):
    self.macro_chief        = MacroChiefAgent(macro, ecb, snb, market, bus)
    self.commodity_chief    = CommodityChiefAgent(market, bus)
    self.sentiment_chief    = SentimentChiefAgent(market, bus)
    self.yield_curve_chief  = YieldCurveChiefAgent(macro, ecb, snb, bus)
    self.sector_chief       = SectorChiefAgent(market, bus)
```

**BottomUpOrchestrator** (21 Agents → 5 Chiefs):
```python
def __init__(self, fundamentals, macro, market, llm, bus):
    self.equity_chief          = EquityChiefAgent(fundamentals, market, llm, bus)
    self.bond_chief            = BondChiefAgent(fundamentals, macro, bus)
    self.index_chief           = IndexChiefAgent(market, bus)
    self.commodity_chief       = CommodityChiefAgent(market, bus)
    self.precious_metals_chief = PreciousMetalsChiefAgent(macro, market, bus)
```

**JudgmentOrchestrator** (3 Agents → 3 Chiefs):
```python
def __init__(self, llm, bus, memory):
    self.anomaly_chief    = AnomalyChiefAgent(bus)
    self.judgment_chief   = JudgmentChiefAgent(llm, bus)
    self.backtester_chief = BacktesterChiefAgent(memory, bus)
```

## Änderungsübersicht

| Datei/Bereich | Änderung |
|---------------|----------|
| `core/domain/models.py` | `EquityChiefResult` hinzufügen |
| `core/domain/events.py` | 12 neue ChiefReady-Events |
| `agents/market_cockpit/` | 5 neue ChiefAgent-Files |
| `agents/stock_deep_dive/` | 5 neue ChiefAgent-Files |
| `agents/` (root) | 3 neue ChiefAgent-Files |
| `orchestrators/` | 3 Files vereinfachen |

Sub-Agents werden nicht verändert.
