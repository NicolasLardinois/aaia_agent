# AAIA — Adaptive AI Investment Agent

**Modul:** Business Intelligence | FHNW  
**Thema:** Entscheidungsagent mit 10 Erweiterungen (Russell & Norvig Framework)

---

## Übersicht

AAIA ist ein vollständiges **Multi-Agenten-Wirtschaftsentscheidungssystem**, das Live-Daten der [FRED API](https://fred.stlouisfed.org/) nutzt, um laufend die optimale Portfolioallokation zwischen **Aktien, Anleihen, Cash und Gold** zu berechnen.

Das System implementiert alle Agenten-Typen aus der Vorlesung:
- **Simple Reflex Agent** → Anomalie-Erkennung (Slide 14)
- **Model-based Reflex Agent** → Wirtschaftsphasen-Modell (Slide 15)
- **Goal-based Agent** → Optimales Portfolio finden (Slide 16)
- **Utility-based Agent** → Nutzenfunktion pro Portfolio (Slide 17)
- **Learning Agent** → Langzeitgedächtnis + Backtesting (Slide 18)
- **Multi-Agent System** → 4 Spezialagenten + Orchestrator (Slide 48)

---

## Architektur

```
FRED API
   │
   ▼
sensors.py          ← Erweiterung 4: Prädiktive Sensoren (BEOBACHTEN)
   │
   ├──► phase_detector.py   ← Erweiterung 2: Phasenerkennung
   ├──► anomaly.py          ← Erweiterung 9: Anomalie-Erkennung
   ├──► memory.py           ← Erweiterung 5: Langzeitgedächtnis
   │
   ▼
orchestrator.py     ← Erweiterung 8: Multi-Agenten (DENKEN)
   ├── MacroAgent      (Makroökonom,    35%)
   ├── LaborAgent      (Arbeitsmarkt,   20%)
   ├── SentimentAgent  (Marktsentiment, 25%)
   └── RiskAgent       (Risiko,         20%)
   │
   ▼
weights.py          ← Erweiterung 3: Dynamische Phasen-Gewichte
confidence.py       ← Erweiterung 6: Konfidenz & Unsicherheit
backtester.py       ← Erweiterung 7: Selbst-Evaluation
explainer.py        ← Erweiterung 10: XAI Erklärbarkeit
   │
   ▼
portfolio.py        ← Erweiterung 1: Softmax-Allokation (HANDELN)
   │
   ▼
main.py             ← Agent Loop (Slide 36)
```

---

## Die 10 Erweiterungen

| # | Erweiterung | Datei | Vorlesungs-Bezug |
|---|-------------|-------|-----------------|
| 1 | Softmax-Portfolioallokation | `portfolio.py` | Slide 17 (Utility) |
| 2 | Wirtschaftsphasen-Erkennung | `phase_detector.py` | Slide 15 (Model-based) |
| 3 | Dynamische Phasen-Gewichte | `weights.py` | Slide 17 (Utility) |
| 4 | Prädiktive Sensoren | `sensors.py` | Slide 14 (Reflex) |
| 5 | Langzeitgedächtnis | `memory.py` | Slide 50 (Memory) |
| 6 | Konfidenz & Unsicherheit | `confidence.py` | Slide 17 (Utility) |
| 7 | Selbst-Evaluation (Backtesting) | `backtester.py` | Slide 18 (Learning) |
| 8 | Multi-Agenten-System | `specialist_agents.py` + `orchestrator.py` | Slide 48 (MAS) |
| 9 | Anomalie-Erkennung | `anomaly.py` | Slide 14 (Reflex) |
| 10 | Erklärbarkeit (XAI) | `explainer.py` | Slide 17 (Utility) |

---

## Wirtschaftsindikatoren (FRED API)

| Indikator | FRED-Code | Bedeutung |
|-----------|-----------|-----------|
| Inflation | CPIAUCSL | Verbraucherpreisindex (YoY %) |
| Arbeitslosigkeit | UNRATE | Arbeitslosenquote (%) |
| Leitzins | FEDFUNDS | Fed Funds Rate (%) |
| Zinskurve | T10Y2Y | 10J-2J Treasury Spread |
| BIP-Wachstum | GDP | Bruttoinlandsprodukt (QoQ %) |
| Konsumentenstimmung | UMCSENT | Michigan Consumer Sentiment |
| Industrieproduktion | INDPRO | Industrieproduktionsindex (YoY %) |

---

## Wirtschaftsphasen

| Phase | Beschreibung | Empfohlenes Portfolio |
|-------|-------------|----------------------|
| Boom | Hohes Wachstum, niedrige Arbeitslosigkeit | Aktien |
| Aufschwung | Steigendes Wachstum, moderate Inflation | Aktien |
| Abschwung | Verlangsamung, steigende Risiken | Anleihen |
| Rezession | Negative Wachstumsraten, hohe Arbeitslosigkeit | Cash/Gold |
| Erholung | Aufschwung nach Rezession | Anleihen/Aktien |

---

## Agent Loop (Slide 36)

```
BEOBACHTEN → DENKEN → HANDELN → (Pause) → BEOBACHTEN → ...
```

Pro Iteration führt der Agent 10 Schritte aus:
1. Sensoren: Live-Daten von FRED API laden
2. Trend-Prognose 3 Monate voraus (lineare Regression)
3. Wirtschaftsphase erkennen
4. Anomalien prüfen (Z-Score)
5. Ähnliche Situationen aus Gedächtnis abrufen
6. Multi-Agenten-Abstimmung
7. Konfidenz berechnen
8. Softmax-Portfolioallokation
9. Backtesting (Selbst-Evaluation)
10. XAI-Erklärung generieren + Gedächtnis speichern

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
python main.py
```

---

## Projektstruktur

```
aaia_agent/
├── main.py               ← Haupt-Agentenschleife
├── sensors.py            ← FRED API + Trendprognose
├── phase_detector.py     ← Wirtschaftsphasen-Klassifikation
├── weights.py            ← Dynamische Gewichte + Nutzenfunktion
├── confidence.py         ← Konfidenzberechnung
├── memory.py             ← Langzeitgedächtnis (JSON)
├── specialist_agents.py  ← 4 Spezialagenten
├── orchestrator.py       ← Multi-Agenten-Koordination
├── anomaly.py            ← Z-Score Anomalie-Erkennung
├── backtester.py         ← Selbst-Evaluation
├── explainer.py          ← XAI Erklärbarkeit
├── portfolio.py          ← Softmax-Allokation
├── requirements.txt      ← Python-Abhängigkeiten
├── .env.example          ← API-Key Template
├── .env                  ← API-Key (nicht committen!)
└── agent_memory.json     ← Automatisch generiert
```

---

## Vorlesungsbezug (BI Week 12)

| Konzept | Implementierung |
|---------|----------------|
| Sensor (Slide 13) | `EconomicSensor.get_state()` |
| Aktuator (Slide 13) | `PortfolioAllocator.allocate()` |
| Agent Loop (Slide 36) | `main.py → run_agent_loop()` |
| Utility-Funktion (Slide 17) | `weights.compute_utility()` |
| Gedächtnis (Slide 50) | `AgentMemory` + `agent_memory.json` |
| Multi-Agent (Slide 48) | `Orchestrator` + 4 Spezialagenten |
| Lernen (Slide 18) | `Backtester.evaluate()` |
