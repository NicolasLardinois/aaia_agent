# AAIA — Adaptive AI Investment Agent

**Modul:** Business Intelligence | FHNW  
**Architektur:** EDA + Hexagonal | Multi-Agent System

---

## Was ist AAIA?

AAIA ist ein vollautomatisches, KI-gestütztes Investitionsanalyse-System. Es beobachtet kontinuierlich das globale Marktumfeld — von Inflation und Zinsen über Rohstoffpreise und Marktstimmung bis hin zu Unternehmenskennzahlen — und leitet daraus strukturierte Investitionsentscheidungen ab.

Das System arbeitet in zwei Richtungen: von oben nach unten (Was passiert gerade im Markt als Ganzes?) und von unten nach oben (Ist dieses konkrete Asset kaufenswert?). Beide Perspektiven werden am Ende zu einem einzigen, begründeten Urteil zusammengeführt.

Das Besondere: Hinter jeder Analyse steckt nicht ein einzelner Agent, sondern ein hierarchisches Netz aus über 40 spezialisierten Agenten, die parallel und unabhängig voneinander arbeiten — und deren Ergebnisse stufenweise verdichtet werden.

---

## Die zwei Analyse-Modi

### Modus 1 — Top-Down: Market Cockpit

Das Market Cockpit gibt eine Antwort auf die Frage: *In welcher Phase befindet sich der Markt gerade, und was bedeutet das für die Kapitalallokation?*

Dafür analysiert AAIA gleichzeitig fünf Bereiche — Makroökonomie, Rohstoffe, Marktstimmung, Zinskurven und Sektoren — und synthetisiert daraus ein Gesamtbild. Das Ergebnis ist ein klar klassifiziertes Marktregime (Boom, Aufschwung, Abschwung, Rezession oder Erholung) mit einer Konfidenzangabe.

Die Makroanalyse umfasst dabei unter anderem den **Buffett-Indikator** (Verhältnis von Gesamtmarktkapitalisierung zu BIP) für ~150 Länder weltweit als Bewertungsmassstab sowie den **adjustierten Big Mac Index** als Indikator für Kaufkraftparität und Währungsbewertungen zwischen Ländern.

### Modus 2 — Bottom-Up: Stock Deep Dive

Wird ein konkretes Asset angegeben (z.B. "AAPL", "SPY", "GC=F"), startet eine Tiefenanalyse. Das System erkennt automatisch die Asset-Klasse (Aktie, Anleihe, Index, Rohstoff oder Edelmetall) und aktiviert den entsprechenden Analyse-Pfad.

Für Aktien bedeutet das: Fundamentalanalyse (KGV, EV/EBITDA, DCF-Bewertung), Qualitätsprüfung (Margen, ROIC, Altman-Z), Analyse des Short-Interesses, Insider-Aktivitäten, Gewinntrends, Burggraben-Bewertung nach Warren Buffetts Moat-Konzept und eine Bandbreiten-Bewertung über mehrere Methoden hinweg.

---

## Die Multi-Agenten-Architektur

Das System ist in drei Schichten aufgebaut:

```
Orchestratoren  →  ChiefAgents  →  Sub-Agents
```

### Schicht 1 — Orchestratoren

Orchestratoren sind die oberste Koordinationsebene. Sie starten die Analyse und delegieren sofort an ChiefAgents. Es gibt drei:

- **TopDownOrchestrator** — koordiniert das Market Cockpit (5 ChiefAgents parallel)
- **BottomUpOrchestrator** — erkennt die Asset-Klasse und aktiviert den richtigen ChiefAgent
- **JudgmentOrchestrator** — verbindet Top-Down- und Bottom-Up-Ergebnisse zu einem Urteil

### Schicht 2 — ChiefAgents

ChiefAgents sind Domain-Koordinatoren. Jeder ChiefAgent ist für genau eine fachliche Domäne verantwortlich und kennt seine Sub-Agents in- und auswendig. Er startet sie parallel, fängt Fehler ab und gibt immer ein vollständiges Ergebnis zurück — auch wenn einzelne Datenquellen ausgefallen sind.

**Market Cockpit ChiefAgents:**

| ChiefAgent | Verantwortlich für |
|---|---|
| `MacroChiefAgent` | BIP, Inflation (USA/Eurozone/CH), Zinsen, Geldmenge, Arbeitsmarkt, Kredit, Buffett-Indikator (~150 Länder) |
| `CommodityChiefAgentMakro` | Energie (WTI, Brent, Gas), Industriemetalle, Edelmetalle (makro), Agrar |
| `SentimentChiefAgent` | VIX, VSTOXX, Fear & Greed Index, Put/Call-Ratio |
| `YieldCurveChiefAgent` | Yield Spreads (10J/2J, 10J/3M, 30J/10J), Sovereign Spreads (BTP/Bund, OAT/Bund) |
| `SectorChiefAgent` | Sektor-Performance (USA/Eurozone), Sektor-Rotation nach Regime |

**Stock Deep Dive ChiefAgents:**

| ChiefAgent | Asset-Klasse | Analysiert |
|---|---|---|
| `EquityChiefAgent` | Aktien | Fundamentals, Quality, Short Interest, Insider, Earnings Trend, Moat, Valuation Range |
| `BondChiefAgent` | Anleihen | Metrics, Duration, Credit Rating, Spread |
| `IndexChiefAgent` | Indizes | Preis, Bewertung, Earnings, Breadth, Momentum, Sektorkomposition, Valuation Range |
| `CommodityChiefAgentMikro` | Rohstoffe | Supply/Demand, Saisonalität, COT (Commitment of Traders), Valuation Range |
| `PreciousMetalsChiefAgent` | Edelmetalle | Preisanalyse, Cross-Metal Ratios, Valuation |

**Übergreifende ChiefAgents:**

| ChiefAgent | Funktion |
|---|---|
| `AnomalyChiefAgent` | Erkennt statistische Ausreisser und widersprüchliche Signale (Z-Score-basiert) |
| `BacktesterChiefAgent` | Lädt vergangene Analysen und bewertet die bisherige Treffsicherheit des Systems |
| `JudgmentChiefAgent` | Synthetisiert alles zu einer finalen Empfehlung (BUY / HOLD / SELL / SHORT) mit Konfidenz und XAI-Begründung |

### Schicht 3 — Sub-Agents

Sub-Agents sind die eigentlichen Spezialisten. Jeder Sub-Agent beherrscht genau eine Aufgabe und hat Zugriff auf eine spezifische Datenquelle. Sie wissen nichts voneinander — ihre Koordination übernimmt ausschliesslich der ChiefAgent.

Aktuell gibt es **über 40 Sub-Agents** in 10 Domänen. Die vollständige Übersicht ist in [`docs/agent_structure.md`](docs/agent_structure.md) dokumentiert. Alle Metriken und Kennzahlen je Sub-Agent sind in [`docs/sub_agents_metrics.md`](docs/sub_agents_metrics.md) aufgelistet.

---

## Resilience: Was passiert wenn etwas ausfällt?

AAIA ist darauf ausgelegt, auch bei partiellen Ausfällen immer ein vollständiges Ergebnis zu liefern. Dafür gibt es zwei Sicherheitsebenen:

**Ebene 1 — Sub-Agent fällt aus:** Der ChiefAgent fängt den Fehler ab und ersetzt das Ergebnis mit einem neutralen Fallback-Wert. Die anderen Sub-Agents laufen ungestört weiter.

**Ebene 2 — ChiefAgent fällt aus:** Der Orchestrator fängt den Fehler ab und ersetzt das Ergebnis mit einem neutralen Fallback. Die anderen ChiefAgents laufen ungestört weiter.

Das System gibt niemals einen Hard-Crash zurück. Stattdessen enthält das Ergebnis in einem Fehlerfall neutrale Werte, und die Gesamtkonfidenz des Urteils sinkt entsprechend.

---

## Urteil und Erklärbarkeit (XAI)

Nachdem Top-Down- und Bottom-Up-Analyse abgeschlossen sind, übernimmt der `JudgmentOrchestrator`. Er kombiniert:

- Das Makro-Regime mit Konfidenz (aus dem Market Cockpit)
- Die Asset-spezifische Tiefenanalyse (aus dem Stock Deep Dive)
- Den Anomalie-Report (statistische Ausreisser und Signalwidersprüche)
- Den Backtester-Kontext (historische Treffsicherheit des Systems für diesen Ticker)

Aus diesen vier Inputs berechnet der `JudgmentChiefAgent` eine dynamische Konfidenz (0.0–1.0) und gibt eine finale Empfehlung aus. Liegt die Konfidenz unter 0.50, empfiehlt das System automatisch HOLD — zu viel Widerspruch, zu wenig Sicherheit. Bei unter 0.35 wird zusätzlich Cash-Bias signalisiert.

Zu jeder Empfehlung generiert ein zweiter LLM-Call eine ausführliche **XAI-Erklärung**: Was waren die entscheidenden Signale? Wo lagen die Widersprüche? Warum diese Konfidenz? Was könnte die Einschätzung kippen?

---

## Bewertungsmethoden

AAIA kombiniert klassische und unkonventionelle Bewertungsansätze:

**Für Einzelaktien und Indizes:**
- KGV-Multiple, EV/EBITDA-Multiple, DCF (Discounted Cashflow)
- **Shiller-CAPE** (Cyclically Adjusted P/E): Glättet Gewinne über 10 Jahre, um Bewertungszyklen sichtbar zu machen
- Altman-Z Score (Insolvenzwahrscheinlichkeit)
- Burggraben-Analyse (Moat) nach Warren Buffetts Konzept: immaterielle Werte, Wechselkosten, Netzwerkeffekte, Kostenvorteile, effiziente Skalierung

**Für den Gesamtmarkt:**
- **Buffett-Indikator** (Total Market Cap / BIP): Globale Implementierung für ~150 Länder. USA via FRED (Echtzeit, monatlich), alle anderen via Weltbank API (jährlich). Jedes Land wird gegen seine **eigene** 10-Jahres-Geschichte verglichen (Z-Score) — nicht gegen einen universellen Schwellenwert. Relevant nur für Aktien, ETFs und Indizes.

  *Dagegen spricht:*
  - **Globalisierung** — S&P 500-Unternehmen erwirtschaften einen Grossteil ihrer Gewinne ausserhalb der USA; das BIP misst aber nur die US-Wirtschaft → strukturell verzerrter Vergleich
  - **Zinsniveau wird ignoriert** — bei 0 % Zinsen sind höhere Bewertungen rational; der Indikator kennt keinen Zinskontext
  - **Kein Timing-Tool** — der Indikator kann jahrelang „überteuert" anzeigen, ohne dass der Markt fällt (z. B. 2016–2021)
  - **Aktienrückkäufe** — erhöhen die Marktkapitalisierung ohne realwirtschaftlichen Gegenwert und verzerren den Quotienten strukturell nach oben

**Für Währungs- und Kaufkraftanalyse:**
- **Adjustierter Big Mac Index**: Vergleicht Kaufkraftparität zwischen Ländern adjustiert für Einkommensniveaus — hilft bei der Einschätzung von Währungsüber- oder -unterbewertungen im globalen Kontext

---

## Datenspeicherung und Backtesting

Jede abgeschlossene Analyse wird in einer **Supabase-Datenbank (PostgreSQL)** gespeichert — inklusive Ticker, Asset-Klasse, Regime, Empfehlung, Konfidenz, Kurs zum Analysezeitpunkt und der vollständigen XAI-Erklärung.

Täglich um 08:00 Uhr läuft ein **Background-Runner** (Windows Task Scheduler), der alle vergangenen Analysen mit der tatsächlichen Kursentwicklung vergleicht:

- `TopDownBacktesterAgent` — war das vorhergesagte Regime korrekt? (30/60/90 Tage)
- `BottomUpBacktesterAgent` — hat das dominante Signal (bullish/bearish/neutral) gestimmt?
- `JudgmentBacktesterAgent` — war BUY/SELL/HOLD/SHORT tatsächlich profitabel?

Die Treffsicherheits-Statistiken fliessen direkt in die Konfidenzberechnung der nächsten Analyse ein. Das System verbessert sich damit kontinuierlich selbst.

Zusätzlich überwacht der `PortfolioMonitorAgent` täglich das Portfolio auf Klumpenrisiken (Sektor, Asset-Klasse, Geographie) und offene Verlustpositionen.

---

## Technologie-Stack

| Komponente | Technologie |
|---|---|
| Sprache | Python 3.12 |
| Async | `asyncio` — alle Sub-Agents laufen parallel |
| Daten | FRED API, Yahoo Finance, Finnhub, ECB/SNB, Weltbank API, CBOE, FMP |
| LLM | Claude (Anthropic) — Moat-Analyse und XAI-Erklärungen |
| Event Bus | Redis — Agenten kommunizieren über Events (EDA) |
| Datenbank | Supabase / PostgreSQL — Analyse-History und Backtester-Reports |
| Caching | In-Memory Cache für API-Responses |

---

## Architekturprinzipien

AAIA folgt zwei Architekturmustern, die zusammen eine klare Trennung von Fachlogik und Infrastruktur sicherstellen:

**EDA (Event-Driven Architecture):** Jeder Agent publiziert nach Abschluss ein Event auf dem Bus (z.B. `MacroChiefReady`, `EquityChiefReady`). Diese Events ermöglichen es dem System, auf Ergebnisse zu reagieren ohne direkte Abhängigkeiten zwischen den Agenten zu erzeugen.

**Hexagonale Architektur (Ports & Adapters):** Die Kern-Fachlogik (`core/domain/`, `agents/`) kennt keine konkreten Datenquellen. Sie kommuniziert ausschliesslich über abstrakte Interfaces (`Ports`). Die konkreten Implementierungen (FRED-API, Yahoo Finance, Redis, Supabase) stecken in `adapters/`. Dadurch lässt sich jede Datenquelle austauschen ohne den Kern zu berühren.

---

## Installation & Ausführung

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. API-Keys konfigurieren
cp .env.example .env
# FRED_API_KEY  — kostenlos: https://fred.stlouisfed.org/docs/api/api_key.html
# FMP_API_KEY   — für EU/CH Shiller-CAPE und Rohstoffpreise (LME)
# ANTHROPIC_API_KEY, SUPABASE_DB_URL

# 3. Market Cockpit aktualisieren (Hintergrundprozess)
python -m app.main dashboard

# 4. Aktie analysieren
# market: USA | CH | ISO-2 Länderkode (DE, FR, IT, ES, NL, ...)
python -m app.main judge AAPL USA
python -m app.main judge NESN.SW CH
python -m app.main judge MC.PA FR
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
│   └── main.py                      ← Einstiegspunkt
│
├── orchestrators/
│   ├── top_down_orchestrator.py     ← Modus 1
│   ├── bottom_up_orchestrator.py    ← Modus 2
│   └── judgment_orchestrator.py     ← Urteil
│
├── agents/                          ← siehe docs/agent_structure.md
│   ├── market_cockpit/              ← Top-Down ChiefAgents + Sub-Agents
│   ├── stock_deep_dive/             ← Bottom-Up ChiefAgents + Sub-Agents
│   ├── anomaly_chief_agent.py
│   ├── backtester_chief_agent.py
│   └── judgment_chief_agent.py
│
├── core/
│   ├── domain/
│   │   ├── models.py                ← Alle Domain-Modelle (Snapshots, Results)
│   │   ├── events.py                ← EDA-Events (AgentReady-Events)
│   │   ├── regime.py                ← Wirtschaftsphasen-Logik
│   │   └── recommendation.py       ← Empfehlungs-Logik
│   └── ports/
│       ├── data_provider.py         ← Abstrakte Daten-Interfaces
│       ├── event_bus.py             ← Event-Bus-Interface
│       ├── llm_provider.py          ← LLM-Interface
│       └── memory_port.py           ← Datenbank-Interface
│
├── adapters/
│   ├── data/                        ← FRED, Yahoo Finance, Finnhub, ECB/SNB
│   ├── event_bus/                   ← Redis
│   ├── llm/                         ← Claude (Anthropic)
│   └── cache/                       ← In-Memory Cache
│
├── config/
│   └── settings.py
│
├── tests/
│
├── docs/
│   ├── agent_structure.md           ← Vollständige Agent-Übersicht
│   └── sub_agents_metrics.md        ← Alle Metriken & Kennzahlen je Sub-Agent
│
└── archive/                         ← Alte Implementierung (v1, Einzeldatei-System)
```
