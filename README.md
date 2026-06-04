# AAIA — Adaptive AI Investment Agent

**Modul:** Business Intelligence | FHNW  
**Architektur:** EDA + Hexagonal | Multi-Agent System

---

## Übersicht

AAIA ist ein vollständiges **Multi-Agenten-Investitionssystem**, das Live-Marktdaten nutzt, um laufend Makro-, Sentiment- und Asset-Analysen durchzuführen und daraus eine fundierte Investitionsentscheidung abzuleiten.

Das System ist in zwei Modi aufgeteilt:

- **Modus 1 — Top-Down (Market Cockpit):** Makroökonomische Analyse des gesamten Marktumfelds
- **Modus 2 — Bottom-Up (Stock Deep Dive):** Tiefenanalyse eines einzelnen Assets (Aktie, Anleihe, Index, Rohstoff, Edelmetall)

---

## Architektur

Das System folgt einer **EDA + Hexagonalen Architektur** (Event-Driven Architecture + Ports & Adapters):

```
Externe Datenquellen (FRED, Yahoo Finance, Finnhub, ECB/SNB)
        │
        ▼
   adapters/data/          ← Ports & Adapters (Infrastruktur)
        │
        ▼
   orchestrators/
   ├── TopDownOrchestrator     ← Modus 1: koordiniert 5 ChiefAgents
   ├── BottomUpOrchestrator    ← Modus 2: verzweigt nach Asset-Klasse
   └── JudgmentOrchestrator    ← Urteil: Anomalie + Backtester + Judgment
        │
        ▼
   agents/
   ├── market_cockpit/         ← Top-Down ChiefAgents + Sub-Agents
   └── stock_deep_dive/        ← Bottom-Up ChiefAgents + Sub-Agents
        │
        ▼
   core/domain/models.py       ← Domain-Modelle & Events
```

---

## Agenten-Struktur

Siehe [`docs/agent_structure.md`](docs/agent_structure.md) für die vollständige Übersicht.

**Market Cockpit (Top-Down):**

| ChiefAgent | Sub-Agents |
|---|---|
| `MacroChiefAgent` | GDP, Inflation, Zinsen, Kredit, Arbeitsmarkt, Geldmenge, Shiller-CAPE |
| `CommodityChiefAgentMakro` | Energie, Industriemetalle, Edelmetalle (Makro), Agrar |
| `SentimentChiefAgent` | VIX, Fear & Greed, Put/Call-Ratio |
| `YieldCurveChiefAgent` | Yield Spread, Sovereign Spread |
| `SectorChiefAgent` | Sektor-Performance, Sektor-Rotation |

**Stock Deep Dive (Bottom-Up):**

| ChiefAgent | Asset-Klasse | Sub-Agents |
|---|---|---|
| `EquityChiefAgent` | Aktien | Fundamentals, Quality, Short Interest, Insider, Earnings Trend, Moat, Valuation Range |
| `BondChiefAgent` | Anleihen | Bond Metrics, Duration, Credit, Spread |
| `IndexChiefAgent` | Indizes | Price, Valuation, Earnings, Breadth, Momentum, Sector Composition, Valuation Range |
| `CommodityChiefAgentMikro` | Rohstoffe | Supply/Demand, Seasonality, COT, Valuation Range |
| `PreciousMetalsChiefAgent` | Edelmetalle | Price, Cross-Metal, Valuation |

**Übergreifende Agents:**

| Agent | Funktion |
|---|---|
| `AnomalyChiefAgent` | Erkennt Anomalien in Top-Down- und Bottom-Up-Ergebnissen |
| `BacktesterChiefAgent` | Evaluiert Entscheidungen rückwirkend |
| `JudgmentChiefAgent` | Synthetisiert Gesamturteil aus allen Ergebnissen |

---

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.12 |
| Async | `asyncio` (parallele Agent-Ausführung) |
| Daten | FRED API, Yahoo Finance, Finnhub, ECB/SNB |
| LLM | Claude (Anthropic) via `adapters/llm/claude_adapter.py` |
| Event Bus | Redis (`adapters/event_bus/redis_bus.py`) |
| Caching | `adapters/cache/result_cache.py` |

---

## Installation & Ausführung

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. API-Key konfigurieren
cp .env.example .env
# .env öffnen und FRED_API_KEY eintragen
# Kostenloser Key: https://fred.stlouisfed.org/docs/api/api_key.html

# 3. Agent starten
python app/main.py
```

---

## Tests ausführen

```bash
pytest tests/ -v
```

---

## Projektstruktur

```
aaia_agent/
├── app/
│   └── main.py                  ← Einstiegspunkt
│
├── orchestrators/
│   ├── top_down_orchestrator.py
│   ├── bottom_up_orchestrator.py
│   └── judgment_orchestrator.py
│
├── agents/                      ← siehe docs/agent_structure.md
│
├── core/
│   ├── domain/
│   │   ├── models.py            ← Alle Domain-Modelle
│   │   ├── events.py            ← EDA-Events
│   │   ├── regime.py            ← Wirtschaftsphasen-Enum
│   │   └── recommendation.py
│   └── ports/
│       ├── data_provider.py     ← Abstrakte Daten-Interfaces
│       ├── event_bus.py
│       ├── llm_provider.py
│       └── memory_port.py
│
├── adapters/
│   ├── data/                    ← FRED, Yahoo Finance, Finnhub, ECB/SNB
│   ├── event_bus/               ← Redis
│   ├── llm/                     ← Claude
│   └── cache/
│
├── config/
│   └── settings.py
│
├── tests/
│
├── docs/
│   └── agent_structure.md
│
└── archive/                     ← Alte Implementierung (v1)
```
