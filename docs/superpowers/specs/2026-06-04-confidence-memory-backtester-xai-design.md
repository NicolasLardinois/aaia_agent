# Design Spec: Confidence, Memory, Backtester, Anomalie, Portfolio, XAI
**Datum:** 2026-06-04
**Status:** Genehmigt

---

## Überblick

Integration von 6 neuen Features in das bestehende Multi-Agenten Finanzsystem (EDA + Hexagonal Architektur). Das System besteht aus zwei bestehenden Flows (TopDown / BottomUp / Judgment) und erhält einen neuen täglichen Background-Flow.

---

## 1. Gesamtarchitektur

### Ansatz
Direkte Integration in bestehende Orchestratoren + separater `background_runner.py` für tägliche Hintergrundaufgaben. Kein neues Event-Bus-Konzept, kein Oversight-Orchestrator.

### Zwei Flows

**Analyse-Flow (auf Anfrage des Users):**
```
TopDownOrchestrator  →  CockpitResult
                     └► TopDownAnomalyAgent  →  AnomalyReport (TopDown)

BottomUpOrchestrator →  BottomUpResult
                     └► BottomUpAnomalyAgent →  AnomalyReport (BottomUp)

JudgmentOrchestrator:
  - lädt letzten BacktesterContext aus Supabase
  - ruft JudgmentAgent auf mit: CockpitResult + BottomUpResult
    + AnomalyReport (TopDown) + AnomalyReport (BottomUp) + BacktesterContext
  - speichert DeepDiveResult in Supabase (analysis_memory)
```

**Background-Flow (täglich 08:00, Windows Task Scheduler):**
```
background_runner.py:
  1. TopDownBacktesterAgent    → bewertet vergangene Regime-Einschätzungen
  2. BottomUpBacktesterAgent   → bewertet vergangene Signale via Kursdaten
  3. JudgmentBacktesterAgent   → bewertet BUY/SELL/HOLD/SHORT via Kursdaten
  4. PortfolioMonitorAgent     → Klumpenrisiko-Check (überspringt wenn leer)
  alle schreiben nach Supabase
```

### Neue Ordnerstruktur
```
agents/
  anomaly/
    top_down_anomaly_agent.py
    bottom_up_anomaly_agent.py
  backtester/
    top_down_backtester_agent.py
    bottom_up_backtester_agent.py
    judgment_backtester_agent.py
  portfolio/
    portfolio_monitor_agent.py

adapters/
  memory/
    supabase_memory.py

core/
  ports/
    memory_port.py

data/
  portfolio.json

background_runner.py
```

---

## 2. Datenbank (Supabase / PostgreSQL)

### Anbieter
**Supabase** — kostenloses PostgreSQL (500 MB, dauerhaft). Verbindung via `psycopg2`.

### Tabelle: `analysis_memory`
Speichert jede abgeschlossene Analyse.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | UUID | Primärschlüssel |
| timestamp | TIMESTAMPTZ | Analysezeitpunkt |
| ticker | VARCHAR | z.B. "AAPL" |
| asset_class | VARCHAR | equity / bond / index / commodity / precious_metal |
| market | VARCHAR | USA / EU / CH |
| regime | VARCHAR | Boom / Aufschwung / Abschwung / Rezession / Erholung |
| regime_confidence | FLOAT | Konfidenz des Regime-Detektors |
| top_down_context | TEXT | abgeleiteter Top-Down-Kontext |
| alignment | VARCHAR | aligned_bullish / contradicting / mixed / aligned_bearish |
| dominant_signal | VARCHAR | bullish / bearish / neutral |
| recommendation | VARCHAR | BUY / SELL / HOLD / SHORT |
| confidence | FLOAT | dynamisch berechnete Gesamtkonfidenz [0.0–1.0] |
| xai_explanation | TEXT | ausführliche LLM-generierte Erklärung |
| price_at_analysis | FLOAT | Kurs zum Analysezeitpunkt |
| top_down_anomaly_severity | VARCHAR | none / low / medium / high |
| bottom_up_anomaly_severity | VARCHAR | none / low / medium / high |

### Tabelle: `backtester_reports`
Tägliche Auswertung der drei Backtester.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | UUID | Primärschlüssel |
| timestamp | TIMESTAMPTZ | Zeitpunkt der Auswertung |
| backtester_type | VARCHAR | topdown / bottomup / judgment |
| ticker | VARCHAR | betroffener Ticker (NULL für topdown) |
| original_recommendation | VARCHAR | ursprüngliche Empfehlung |
| price_at_recommendation | FLOAT | Kurs zum Empfehlungszeitpunkt |
| price_today | FLOAT | heutiger Kurs |
| return_pct | FLOAT | Rendite in % |
| verdict | VARCHAR | correct / incorrect / neutral |
| accuracy_30d | FLOAT | Treffsicherheit letzte 30 Tage (nur topdown) |
| accuracy_60d | FLOAT | Treffsicherheit letzte 60 Tage (nur topdown) |
| accuracy_90d | FLOAT | Treffsicherheit letzte 90 Tage (nur topdown) |
| notes | TEXT | Zusätzliche Hinweise |

### Tabelle: `portfolio_snapshots`
Täglicher Portfolio-Gesundheitsbericht.

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | UUID | Primärschlüssel |
| timestamp | TIMESTAMPTZ | Zeitpunkt |
| total_positions | INT | Anzahl Positionen |
| total_value_usd | FLOAT | Gesamtwert in USD |
| cluster_risks | JSONB | Klumpenrisiken mit Details |
| alerts | JSONB | Liste aktiver Warnungen |
| overall_health | VARCHAR | green / yellow / red |

---

## 3. Neue Komponenten

### 3.1 AnomalyReport (Domain-Objekt)

```python
@dataclass
class AnomalyReport:
    has_anomalies: bool
    statistical: list[str]    # Z-Score Ausreisser, je ein lesbarer Satz
    contradictions: list[str] # Widersprüchliche Signale, je ein lesbarer Satz
    severity: str             # "none" | "low" | "medium" | "high"
    summary: str              # kompakter Text für JudgmentAgent-Prompt
```

**Severity-Logik:**
- `none`: keine Anomalien
- `low`: 1 statistische Anomalie oder 1 Widerspruch
- `medium`: 2+ statistische Anomalien oder 2+ Widersprüche
- `high`: statistische Anomalie UND Widersprüche gleichzeitig

### 3.2 TopDownAnomalyAgent

**Input:** `CockpitResult`, `history: list[dict]` (letzte 90 Tage aus Memory)

**Statistische Anomalien (Z-Score > 2.5):**
- VIX vs. historischem Durchschnitt
- Fear & Greed Index vs. historischem Durchschnitt
- Yield Spreads vs. historischem Durchschnitt
- Inflation vs. historischem Durchschnitt
- Regime-Konfidenz (sehr tief = Anomalie)

**Widersprüche:**
- Ein Widerspruch liegt vor wenn ein Bereich BULLISH und ein anderer BEARISH signalisiert (nicht bloss NEUTRAL).
- Konkrete Paare die geprüft werden: Macro vs. Sentiment, Macro vs. YieldCurve, Commodity vs. Macro.
- Wenn ≥ 2 dieser Paare widersprechen → Anomalie vom Typ "Widerspruch".

**Output:** `AnomalyReport`

### 3.3 BottomUpAnomalyAgent

**Input:** `BottomUpResult`, `history: list[dict]` (letzte 90 Tage aus Memory für diesen Ticker)

**Statistische Anomalien (Z-Score > 2.5):**
- KGV vs. historischem Durchschnitt (equity)
- Short Float % vs. historischem Durchschnitt (equity)
- Insider-Aktivität (ungewöhnlich viele Transaktionen)

**Widersprüche (equity):**
- Fundamentals=BULLISH aber Valuation=BEARISH
- Earnings=BULLISH aber Quality=BEARISH
- Wenn ≥ 3 von 6 Bottom-Up-Signalen widersprechen → Widerspruch

**Hinweis:** Bei weniger als 5 historischen Einträgen für diesen Ticker → nur Widerspruchs-Erkennung, keine Z-Score-Berechnung.

**Output:** `AnomalyReport`

### 3.4 JudgmentAgent — Erweiterungen

**Neuer Input:**
```python
async def run(
    self,
    ...  # alles wie bisher
    top_down_anomaly: AnomalyReport,
    bottom_up_anomaly: AnomalyReport,
    backtester_context: dict,
) -> DeepDiveResult:
```

**Erweiterter Prompt (LLM-Call 1):**
```
... (bestehender Prompt-Inhalt) ...

TOP-DOWN ANOMALIEN: {top_down_anomaly.summary}
BOTTOM-UP ANOMALIEN: {bottom_up_anomaly.summary}
SYSTEM-TREFFSICHERHEIT: {backtester_context.summary}
```

**Confidence-Berechnung (nach LLM-Call 1):**
```
Basis: 0.70

Abzüge:
  alignment == "contradicting"        → -0.15
  alignment == "mixed"                → -0.05
  top_down_anomaly.severity == "low"  → -0.05
  top_down_anomaly.severity == "medium" → -0.15
  top_down_anomaly.severity == "high" → -0.25
  bottom_up_anomaly.severity == "low" → -0.05
  bottom_up_anomaly.severity == "medium" → -0.15
  bottom_up_anomaly.severity == "high" → -0.25
  regime_confidence < 0.4             → -0.10

Aufschläge:
  alignment == "aligned_bullish" oder "aligned_bearish" → +0.10

Finale Konfidenz = max(0.10, min(1.0, Basis + Summe))
```

**Cash-Bias-Logik:**
```
confidence < 0.50:
  → Empfehlung = HOLD
  → Hinweis: "Signallage zu widersprüchlich — Abwarten empfohlen."

confidence < 0.35:
  → Empfehlung = HOLD
  → Hinweis: "Stark widersprüchliche oder anomale Signale — Cash bevorzugen,
               kein neues Kapital einsetzen."
```

**XAI (LLM-Call 2, separater System-Prompt):**
```
System: "Du bist ein erfahrener Finanzanalyst. Erkläre die getroffene Empfehlung
ausführlich und nachvollziehbar. Struktur: (1) Top-Down-Analyse: welche Signale
waren entscheidend und warum, (2) Bottom-Up-Analyse: welche Kennzahlen haben
die Entscheidung beeinflusst, (3) Widersprüche: wo lagen sie und wie wurden sie
aufgelöst, (4) Konfidenz: warum diese Stufe, (5) Kipppunkte: was könnte die
Einschätzung ändern. Kein Fachjargon. Direkt und klar."
```

### 3.5 PortfolioMonitorAgent

**Input:** `data/portfolio.json`

**Portfolio-Format:**
```json
{
  "positions": [
    {
      "ticker": "AAPL",
      "shares": 10,
      "buy_price": 175.0,
      "asset_class": "equity",
      "sector": "Technology",
      "country": "USA"
    }
  ]
}
```

**Checks (wenn Positionen vorhanden):**
- Klumpenrisiko Sektor: Warnung wenn > 40% in einem Sektor
- Klumpenrisiko Asset-Klasse: Warnung wenn > 80% in einer Asset-Klasse
- Klumpenrisiko Geographie: Warnung wenn > 70% in einem Land
- Offene Verluste: Warnung wenn Position > 15% unter Kaufpreis
- Alignment-Check: Warnung wenn letzte Analyse SELL/SHORT für eine gehaltene Position

**Severity:**
- 0 Warnungen → `green`
- 1–2 Warnungen → `yellow`
- 3+ Warnungen → `red`

### 3.6 Backtester-Agenten

**TopDownBacktesterAgent:**
- Lädt alle Analysen der letzten 90 Tage aus `analysis_memory`
- Gruppiert nach ursprünglichem Regime
- Vergleicht mit aktuellem Regime (FRED-API-Call)
- Berechnet Treffsicherheit: 30d / 60d / 90d
- "Korrekt" = gleiches Regime oder direkt benachbartes Regime im Zyklus (Boom↔Aufschwung, Aufschwung↔Erholung, Erholung↔Abschwung, Abschwung↔Rezession). Zwei oder mehr Stufen Abweichung (z.B. Boom→Rezession) gilt als "incorrect".

**BottomUpBacktesterAgent:**
- Lädt alle Analysen mit `dominant_signal` aus `analysis_memory`
- Holt aktuellen Kurs via Yahoo Finance für jeden Ticker
- "Korrekt": BULLISH + Kurs gestiegen ≥ 2% / BEARISH + Kurs gefallen ≥ 2% / NEUTRAL + Kurs ±2%

**JudgmentBacktesterAgent:**
- Lädt alle `recommendation` aus `analysis_memory`
- Holt aktuellen Kurs für jeden Ticker
- "Korrekt": BUY + Kurs gestiegen ≥ 3% / SELL + Kurs gefallen ≥ 3% / HOLD + Kurs ±5% / SHORT + Kurs gefallen ≥ 3%
- Schreibt Gesamttreffsicherheit als Kontext für nächsten JudgmentAgent-Run

---

## 4. Änderungen an bestehenden Dateien

| Datei | Art der Änderung |
|-------|-----------------|
| `core/domain/models.py` | `AnomalyReport` hinzufügen, `DeepDiveResult` um `confidence` + `xai_explanation` erweitern |
| `core/ports/memory_port.py` | Neue Datei — Hexagonal-Port (ABC) |
| `core/domain/recommendation.py` | `confidence` Parameter statt hardcoded Werte |
| `agents/judgment/judgment_agent.py` | Neuer Input, Confidence-Berechnung, XAI LLM-Call |
| `orchestrators/judgment_orchestrator.py` | Anomalie-Agenten aufrufen, Memory laden/speichern |

---

## 5. Hexagonal-Port: MemoryPort

```python
class MemoryPort(ABC):
    def save_analysis(self, result: DeepDiveResult, price: float) -> None: ...
    def load_history(self, ticker: str, days: int = 90) -> list[dict]: ...
    def load_global_history(self, days: int = 90) -> list[dict]: ...
    def load_latest_backtester_report(self, backtester_type: str) -> dict: ...
    def save_backtester_report(self, report: dict) -> None: ...
    def save_portfolio_snapshot(self, snapshot: dict) -> None: ...
    def load_latest_portfolio_snapshot(self) -> dict | None: ...
```

Implementierung: `adapters/memory/supabase_memory.py` via `psycopg2`.

---

## 6. Background-Runner

**Datei:** `background_runner.py` (im Projektstamm)

**Einrichtung Windows Task Scheduler:**
- Trigger: Täglich 08:00
- Aktion: `python C:\Users\nicil\aaia_agent\background_runner.py`
- Arbeitsverzeichnis: `C:\Users\nicil\aaia_agent`

**Ablauf:**
```python
async def main():
    memory = SupabaseMemory()
    macro  = FredDataProvider()
    market = YahooFinanceProvider()

    await TopDownBacktesterAgent(memory, macro).run()
    await BottomUpBacktesterAgent(memory, market).run()
    await JudgmentBacktesterAgent(memory, market).run()
    await PortfolioMonitorAgent(memory, market).run()
```

**Fehlerbehandlung:** Jeder Agent läuft in einem try/except — schlägt ein Agent fehl, laufen die anderen trotzdem.

---

## 7. Abhängigkeiten (requirements.txt Ergänzungen)

```
psycopg2-binary    # Supabase / PostgreSQL Verbindung
yfinance           # Kursdaten für Backtester und Portfolio-Monitor
```

---

## 8. Implementierungsreihenfolge

1. Supabase aufsetzen (Tabellen erstellen, Verbindung testen)
2. `MemoryPort` + `SupabaseMemory` implementieren
3. `AnomalyReport` Domain-Objekt + `models.py` Erweiterungen
4. `TopDownAnomalyAgent` + `BottomUpAnomalyAgent`
5. `JudgmentAgent` erweitern (Confidence + XAI + neuer Input)
6. `JudgmentOrchestrator` erweitern
7. `recommendation.py` vereinfachen
8. `PortfolioMonitorAgent` + `data/portfolio.json`
9. Drei Backtester-Agenten
10. `background_runner.py`
11. Windows Task Scheduler einrichten
