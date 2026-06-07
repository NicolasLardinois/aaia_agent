# Code Review — Full Audit Report
**Datum:** 2026-06-05
**Reviewer:** Claude Code (5 parallele Analyse-Agenten)

---

## Kritische Bugs (Crash / Datenverlust)

### 1. `adapters/cache/result_cache.py:233` — BottomUpResult fehlen 2 Pflichtfelder → TypeError
`BottomUpResult` hat 13 Felder; `load_bottom_up()` übergibt nur 11 — `index` und `commodity_deep` fehlen. Raises `TypeError` jedes Mal wenn eine frische Bottom-Up-Cache-Datei existiert, was der normale Happy Path ist.

**Lösung:** In `load_bottom_up()` die fehlenden beiden Felder `index` und `commodity_deep` aus dem gecachten JSON gelesen und an den `BottomUpResult`-Konstruktor übergeben — analog zu allen anderen 11 Feldern.

### 2. `app/main.py:130` — JudgmentOrchestrator mit 2 Argumenten aufgerufen, braucht 3
```python
orch = JudgmentOrchestrator(llm, bus)   # fehlt: memory
```
`JudgmentOrchestrator.__init__` erfordert `(llm, bus, memory)`. Crasht sofort im `judge`-Modus bevor irgendwas passiert.

**Lösung:** `memory` als drittes Argument ergänzt: `JudgmentOrchestrator(llm, bus, memory)`. Das `memory`-Objekt (`SupabaseMemory`) war bereits weiter oben in `main.py` instanziert — es fehlte nur die Übergabe.

### 3. `adapters/data/finnhub.py` — ALLE Methoden werfen NotImplementedError
Jede Methode enthält nur `raise NotImplementedError("Finnhub Adapter noch nicht implementiert")`. `app/main.py` injiziert diesen als Live-Provider für den gesamten Bottom-Up-Equity-Pfad — `FundamentalsAgent`, `QualityAgent`, `InsiderAgent` usw. crashen alle zur Laufzeit.

**Lösung:** Alle Methoden vollständig neu implementiert — ohne Finnhub, dafür mit drei Datenquellen:
- **yfinance** liefert Basisfelder (KGV, Forward-KGV, Marktkapitalisierung, Schulden, Margen usw.) sowie ~4 Jahre Finanzabschlüsse für den Fallback.
- **SEC EDGAR XBRL API** liefert für US-Aktien bis zu 10 Jahre jährliche EPS-Daten aus offiziellen 10-K-Einreichungen.
- **FRED API** liefert jährliche CPI-Daten für die Inflationsbereinigung (US: `CPIAUCSL`, Eurozone: `CP0000EZ19M086NEST`, Schweiz: `CHECPIALLMINMEI`).
- **FMP (Financial Modeling Prep)** liefert für EU/CH-Aktien bis zu 12 Jahre EPS-Daten, da SEC EDGAR nur US-Firmen abdeckt.

Zusätzlich neu berechnet: WACC (CAPM-Modell mit ERP 5,5%), ROIC (NOPAT / investiertes Kapital), Altman Z-Score, echte 3-Jahres-Umsatz-CAGR und ein 3-stufiges Shiller-KGV (SEC → FMP → yfinance-Fallback).

### 4. `adapters/memory/supabase_memory.py:128–129` — Anomalie-Schweregrade immer "none"
```python
"none",   # top_down_anomaly_severity  ← hartcodiert
"none",   # bottom_up_anomaly_severity ← hartcodiert
```
Die tatsächlichen `AnomalyReport`-Daten werden nie geschrieben. Jede Datenbankzeile speichert permanent "none" für beide Schweregrad-Spalten. Der historische Anomalie-Datensatz ist dauerhaft korrumpiert.

**Lösung:** Die beiden hartcodierten `"none"` durch bedingte Ausdrücke ersetzt, die den echten Schweregrad aus dem `AnomalyReport` lesen:
```python
result.top_down_anomaly.severity if result.top_down_anomaly else "none",
result.bottom_up_anomaly.severity if result.bottom_up_anomaly else "none",
```
Dazu mussten `top_down_anomaly` und `bottom_up_anomaly` als optionale Felder in `DeepDiveResult` (`core/domain/models.py`) ergänzt und im `JudgmentOrchestrator` befüllt werden.

### 5. `adapters/memory/supabase_memory.py` — Verbindung wird nie geschlossen → Connection Pool Leak
`psycopg2.connect()` als Context Manager verwaltet nur Transaktionen, nicht die Verbindungslebensdauer. Jede public Methode öffnet eine neue Verbindung, die nie geschlossen wird. Im Dauerbetrieb erschöpft das den Supabase Connection Pool.

**Lösung:** `_connect()` mit `@contextmanager` (aus `contextlib`) dekoriert und `conn.close()` in einen `finally`-Block verschoben — wird damit garantiert geschlossen, egal ob die Transaktion erfolgreich war oder eine Exception geworfen wurde:
```python
@contextmanager
def _connect(self):
    conn = psycopg2.connect(self.db_url)
    try:
        yield conn
    finally:
        conn.close()
```

### 6. `core/domain/regime.py:17–23` — RECOVERY/SLOWDOWN-Schwellenwerte in falscher Reihenfolge
```python
(MarketRegime.RECOVERY, -0.10),  # greift zuerst für composite in [-0.10, 0.20)
(MarketRegime.SLOWDOWN, -0.40),  # unerreichbar für composite in [-0.10, -0.40)
```
Jeder leicht negative Composite-Wert (z.B. -0.05, der typische Late-Cycle-Zustand) wird als `RECOVERY` klassifiziert statt als `SLOWDOWN`. Die Kernlogik ist systematisch falsch.

**Lösung:** Die gesamte Schwellenwert-Logik durch **Fuzzy Logic mit Gauss'schen Zugehörigkeitsfunktionen** ersetzt. Jede Phase bekommt einen kontinuierlichen Score basierend auf einer Gauss-Kurve mit ihrem typischen Composite-Zentrum und einer definierten Breite. Gewinner ist die Phase mit dem höchsten Score. RECOVERY wird zusätzlich nur aktiviert, wenn ein positiver Trend (steigende Composite-History) erkannt wird — ein bestätigendes Signal, nicht nur ein Schwellenwert. Der Composite-Score-Verlauf wird in `.cache/composite_history.json` persistiert.

### 7. `core/domain/regime.py:7` — Toter Code-Zweig; Inflation 3–4% bekommt neutralen Score
```python
lambda v: 0.5 if 1 < v < 3 else (-0.5 if v > 4 else (-1.0 if v > 6 else 0.0))
```
Wenn `v > 4` zuerst greift, ist `v > 6` unerreichbar — der `-1.0`-Zweig ist toter Code. Werte 3.0–4.0 (überziel-Inflation) fallen durch zu `0.0` (neutraler Score). Hochinflations-Umgebungen werden systematisch untergewichtet.

**Lösung:** Zusammen mit Bug #6 erledigt — die gesamte Lambda-basierte Scoring-Logik wurde durch die Fuzzy-Logic-Implementierung ersetzt. Einzelne fehlerhafte Lambdas existieren nicht mehr.

### 8. `core/domain/recommendation.py:92` — "contradicting" wird als BEARISH klassifiziert → SHORT-Bias
```python
bearish = signal == Signal.BEARISH or alignment in ("aligned_bearish", "contradicting")
```
Wenn Top-Down- und Bottom-Up-Signale widersprechen, behandelt das System es als bearish und kann SHORT empfehlen. Ein Widerspruch sollte HOLD sein.

**Lösung:** `"contradicting"` aus der Bearish-Bedingung entfernt:
```python
bearish = signal == Signal.BEARISH or alignment == "aligned_bearish"
```
Ein widersprechendes Signal fällt damit in keinen der beiden Zweige und landet korrekt bei HOLD.

---

## High Severity Bugs

### 9. `agents/market_cockpit/macro/interest_rate_agent.py:64–66` — None-Rate fügt 0 zur History hinzu, vergiftet Richtungsbestimmung
```python
_RATE_HISTORY["usa"].append(fed_rate or 0)
```
Wenn ein API-Call fehlschlägt und `None` zurückgibt, wird `0` angehängt. Beim nächsten erfolgreichen Aufruf wird der echte Kurs mit `0` verglichen und `_direction` meldet "rising" — ein fabriziertes Signal durch einen fehlgeschlagenen Call. Die History wächst auch unbegrenzt (module-level Liste, wird nie geleert).

### 10. `agents/market_cockpit/macro/interest_rate_agent.py:62` — Falsy-Zero versteckt Zero-Lower-Bound-Zinsen
```python
usa_real = round(fed_rate - usa_cpi, 3) if fed_rate and usa_cpi else None
```
`if fed_rate` schlägt fehl wenn der Fed-Zinssatz genau `0.0` ist (2020–2021 Umgebung), setzt `usa_real = None` obwohl beide Werte vorhanden und gültig sind.

### 11. `agents/market_cockpit/sector/sector_performance_agent.py:65–68` — Leading/Lagging-Sektor nach absolutem Preis, nicht nach Rendite
`get_current_price` gibt absolute ETF-Preise zurück. XLK (~$200) wird immer "leading" und XLU (~$70) immer "lagging" sein, unabhängig von der tatsächlichen Performance. `SectorRotationAgent` leitet daraus Regime-Alignment-Signale ab, die dauerhaft verzerrt sind.

### 12. `agents/market_cockpit/yield_curve/yield_spread_agent.py:61` — Falsy-Zero ignoriert gültigen Schweizer Spread
```python
ch_spread = round(snb_10y - snb_2y, 3) if snb_10y and snb_2y else None
```
Wenn der SNB 2-Jahres-Yield `0.0` ist (häufig in der Schweizer Negativzins-Ära), wird `ch_spread` zu `None` obwohl gültige Daten vorhanden sind.

### 13. `agents/market_cockpit/commodity/industrial_metals_agent.py:7` — Ungültige Yahoo Finance Ticker
```python
TICKERS = {"zinc": "ZNC=F", "nickel": "NI=F"}
```
Zink und Nickel handeln an der LME, nicht der CME. Diese Ticker geben immer `None` zurück — Zink- und Nickeldaten fehlen bei jedem Run still und heimlich.

### 14. `agents/market_cockpit/sentiment/put_call_agent.py:10` — Ungültiger Ticker `^PCALL`
CBOE Put/Call Ratio ist via Yahoo Finance nicht als `^PCALL` verfügbar. Das gesamte Put/Call-Ratio-Signal ist still deaktiviert — immer `NEUTRAL`.

### 15. `adapters/data/fred_api.py:41–46` — `get_economic_state` hat keine Fehlerbehandlung
Anders als `get_extended_state` wird hier nichts in try/except gewrappt. Jeder FRED-Ausfall oder Rate-Limit für eine einzelne Serie killt die gesamte Methode und crasht `MacroChiefAgent`.

**✅ Gelöst (2026-06-08):** Jede Serie wird jetzt in einem eigenen `try/except`-Block gefetcht — identisch zu `get_extended_state`. Schlägt eine Serie fehl, landet `None` im Dict; die anderen Serien laufen weiter. `MacroChiefAgent` und `RegimeDetector` sehen `None`-Werte statt eines Crashes.

### 16. `adapters/data/fred_api.py:44,52` — `.iloc[-1]` auf leerer Series nach `pct_change(12)`
Nach `pct_change(12)` werden die ersten 12 Observations zu NaN. Bei weniger als 13 Datenpunkten gibt `.iloc[-1]` `NaN` zurück. NaN-Floats fließen in den `RegimeDetector` wo sie als `0` scored werden — stil falsche Regime-Klassifikationen.

**✅ Gelöst (2026-06-08):** Alle Lambdas in `SERIES` und `EXTENDED_SERIES` rufen jetzt `.dropna()` vor `.iloc[-1]` auf. Zusätzlich prüft `get_economic_state()` den Float-Wert mit `np.isnan()` und schreibt `None` statt NaN ins Dict.

### 17. `adapters/llm/claude_adapter.py:22` — IndexError wenn API leere Content-Liste zurückgibt
```python
return message.content[0].text
```
Raises `IndexError` wenn das Modell keine Content-Blöcke zurückgibt (z.B. am Token-Limit gestoppt bevor ein einziges Token generiert wurde).

### 18. `core/domain/top_down_context.py:43` — TypeError wenn `spread_10y2y` None ist und Kurve invertiert
```python
notes.append(f"Zinskurve invertiert ({usa_yield.spread_10y2y:+.2f})")
```
`spread_10y2y` ist `Optional[float]`. Die Guard prüft nur `inverted`, nicht ob der Wert `None` ist. Wenn aus dem Cache geladen ohne dieses Feld, crasht es.

### 19. `adapters/event_bus/redis_bus.py:15–17` — Exception in einem Handler stoppt alle nachfolgenden Handler
```python
for handler in self._handlers.get(type(event), []):
    handler(event)   # Exception hier abbricht die Loop
```
Ein Bug in einem Subscriber verhindert still, dass alle anderen Subscriber das Event empfangen.

### 20. `agents/stock_deep_dive/bond/bond_credit_agent.py:41` — `prefix[:2]` bricht Rating-Lookup
Für Keys wie `"Baa"` ergibt `prefix[:2]` = `"Ba"`, daher matched `"Baa3"` den `"Ba"`-Eintrag (1.2% Ausfallrate, Spekulation) statt `"Baa"` (0.18%, Investment Grade). Falsche Default-Wahrscheinlichkeiten für viele Ratings.

### 21. `agents/stock_deep_dive/precious_metals/precious_metals_valuation_agent.py:52–57` — Invertierter Bewertungsbereich bei positiven Realzinsen
Die Formel produziert `low > high` wenn Realzinsen positiv sind (z.B. 2.5% wie 2025). Jede nachgelagerte `_position`-Prüfung gegen ein invertiertes Band liefert unsinnige Signale.

### 22. `agents/stock_deep_dive/equity/valuation_range_agent.py:63–67` — Division durch Null im DCF
```python
dcf_low = fcf_per_share * (1 + growth * 0.7) / (wacc - terminal_growth)
```
`terminal_growth` ist hardcodiert auf `0.025`. Wenn `wacc == 0.025` (oder niedriger), ist das Division durch Null. Die Guard prüft nur `wacc != None` und `wacc != 0`.

### 23. `agents/market_cockpit/macro/credit_agent.py:28` und `labor_income_agent.py:28` — Keine Fehlerbehandlung in run()
Anders als alle anderen Multi-Provider-Agenten (GDP, Inflation, InterestRate, MoneySupply) wrappen `CreditAgent` und `LaborIncomeAgent` ihre Provider-Calls nicht in try/except. Exception propagiert direkt raus und bricht das Aggregat.

### 24. `agents/anomaly_chief_agent.py:21–25` — `td_anomaly_agent.run()` nicht in try/except gewrappt
```python
td_anomaly = (
    self.td_anomaly_agent.run(cockpit, global_history)
    if cockpit is not None
    else AnomalyReport.empty()
)
```
Wenn es wirft (z.B. None-Attribut-Zugriff auf cockpit), propagiert die Exception raus aus `AnomalyChiefAgent.run()` und wird im JudgmentOrchestrator ohne Logging still zu HOLD/0.0 degradiert.

### 25. `background_runner.py:21–25` — Bypasses BacktesterChiefAgent
```python
agents = [
    ("TopDownBacktester",  TopDownBacktesterAgent(memory).run),
    ("BottomUpBacktester", BottomUpBacktesterAgent(memory).run),
    ("JudgmentBacktester", JudgmentBacktesterAgent(memory).run),
    ...
]
```
`BacktesterChiefAgent` existiert und publiziert ein `BacktesterChiefReady`-Event mit koordinierter Ausführung. Der Background-Runner bypassed das komplett — das Event wird nie publiziert, Ausführung ist sequentiell statt parallel.

---

## Medium Severity Bugs

### 26. `agents/market_cockpit/macro/shiller_cape_agent.py:29` — Kein unterer Schwellenwert für BULLISH
Jeder CAPE-Wert unterhalb des historischen Durchschnitts — ob 1% oder 94% darunter — liefert `BULLISH`. Ein Markt im katastrophalen Zusammenbruch generiert dasselbe Signal wie einer, der leicht unterbewertet ist.

### 27. `agents/market_cockpit/sentiment/fear_greed_agent.py:21–24` — Label/Signal-Mismatch bei Wert 55
`_label(55)` → "Neutral" aber `_signal(55)` → `BEARISH`. Label und Signal widersprechen sich an der Grenze.

### 28. `put_call_agent.py:31` und `sovereign_spread_agent.py:27–28` — Tote Exception-Guards
```python
if isinstance(ratio, Exception):   # Niemals True — asyncio.to_thread wirft, gibt nicht zurück
```
`asyncio.to_thread` wirft Exceptions; gibt sie nie als Return-Werte zurück. Beide Guards sind dauerhaft toter Code.

### 29. `agents/market_cockpit/yield_curve/sovereign_spread_agent.py:13–17` — Doppelter BEARISH-Zweig, unerreichbarer Branch
```python
if btp_bund > 250: return Signal.BEARISH   # "starker Eurozone-Stress"
if btp_bund > 150: return Signal.BEARISH   # "erhöhter Stress" ← identisches Ergebnis
```
Beide Zweige liefern `BEARISH`, keine Unterscheidung. Der zweite Zweig ist strukturell redundant.

### 30. `agents/market_cockpit/macro_chief_agent.py:82` — `EXPANSION` als Default-Regime ist unsicher
Wenn alle Provider ausfallen, erhalten nachgelagerte Sektor-Agenten `regime=EXPANSION` mit 50% Confidence und generieren aktionabel aussehende (aber grundlose) "buy Tech, buy ConsumerDisc" Empfehlungen.

### 31. `core/utils/statistics.py:11` — Population-Varianz statt Stichproben-Varianz
Teilt durch N statt N-1. Bei kleinen History-Fenstern (3–10 Observations) sind Z-Scores um bis zu 22% aufgebläht, was falsche Anomalie-Erkennungen produziert.

### 32. `core/ports/data_provider.py:110–112` — Duplizierte `LLMProvider`-Klassendefinition
Eine zweite `LLMProvider(ABC)`-Klasse existiert in `data_provider.py`, identisch mit der in `llm_provider.py`. `isinstance`-Prüfungen gegen eine schlagen für Instanzen der anderen fehl.

### 33. `adapters/data/fred_api.py:59` — `get_extended_state` ruft redundant `get_economic_state` auf
Jeder Call feuert 7 zusätzliche FRED API HTTP-Requests — verdoppelt die API-Kosten und Latenz.

**✅ Gelöst (2026-06-08):** `get_extended_state` ruft `get_economic_state()` nicht mehr auf. Stattdessen wird `CPIAUCSL` direkt inline gefetcht (1 API-Call statt 7) um den Inflationswert für `real_wage_growth` zu berechnen.

### 34. `agents/stock_deep_dive/bond/bond_metrics_agent.py:47` — `ytm=0.0` wird als fehlende Daten behandelt
`if ytm and inflation` schlägt für Zero-Coupon- oder Null-Zins-Anleihen fehl. Real-Yield wird zu `None` statt `-inflation`, versteckt einen genuinen negativen Real-Yield.

### 35. `agents/stock_deep_dive/index/index_momentum_agent.py:33` — Bearish RSI-Guard greift in ~90% aller Marktlagen
`rsi > 30` ist in nahezu allen normalen Marktbedingungen wahr, macht diesen Guard als Filter bedeutungslos. Asymmetrisch mit dem Bullish-Guard (`rsi < 70`).

### 36. `agents/stock_deep_dive/commodity/supply_demand_agent.py:77` — `_signal` definiert aber nie aufgerufen
`signal=Signal.NEUTRAL` ist hartcodiert. Der Funktionskörper ist toter Code.

### 37. `agents/market_cockpit/commodity/agricultural_agent.py:22–27` — Liefert immer NEUTRAL
Beide Zweige von `_signal` geben `Signal.NEUTRAL` zurück. Der Agricultural Agent trägt nichts zum Commodity-Signal bei.

### 38. `agents/market_cockpit/macro/inflation_agent.py:14–19` — CPI 3.0–4.0% → NEUTRAL; `trend`-Parameter ungenutzt
CPI zwischen 3% und 4% (über Zentralbank-Ziel) wird als neutral klassifiziert. Der `trend`-Parameter ist deklariert aber wird im Funktionskörper nie verwendet.

### 39. `agents/stock_deep_dive/bond/bond_credit_agent.py:27–28` — Unbekanntes Rating defaults zu "investment_grade"
`_category(None)` gibt `"investment_grade"` zurück. Eine Anleihe ohne Rating-Daten wird als Investment Grade klassifiziert — potenziell gefährlich für Risikobewertungen. Sollte `"unrated"` sein.

### 40. `agents/stock_deep_dive/equity/valuation_range_agent.py:74–75` — `min/max`-Aggregation erzeugt künstlich breites Band
```python
combined_low = min(m.low for m in methods)
combined_high = max(m.high for m in methods)
```
Nimmt das pessimistischste Low und optimistischste High aller Methoden — erzeugt ein Band so breit, dass kaum etwas je als "überbewertet" oder "unterbewertet" gilt.

### 41. `agents/stock_deep_dive/index/index_valuation_range_agent.py:49–55` — Einzelne Methode reicht für BULLISH/BEARISH
`total >= 1` triggert "undervalued" BULLISH. Das bedeutet: wenn nur eine der zwei Methoden "undervalued" sagt, ist das Gesamtergebnis BULLISH — zu niedriger Schwellenwert für starke Richtungssignale.

### 42. `agents/stock_deep_dive/index/index_price_agent.py:61–62` — YTD-`searchsorted` auf String kann bei timezone-aware Index fehlschlagen
`close.index.searchsorted(f"{datetime.utcnow().year}-01-01")` kann `TypeError` werfen wenn der Index timezone-aware ist. Zudem: wenn die ersten Handelstage des Jahres nicht im 5-Jahres-Fenster liegen, wird YTD relativ zu 5 Jahren ago berechnet.

### 43. `agents/stock_deep_dive/precious_metals/precious_metals_valuation_agent.py:3,93` — Publiziert equity `ValuationRangeReady` statt eigenem Event
Der Agent importiert und publiziert `ValuationRangeReady` (Equity-Domain), nicht ein dediziertes `PreciousMetalsValuationReady`-Event. Falsche Event-Routing wenn nach Typ gefiltert wird.

### 44. `agents/stock_deep_dive/equity/fundamentals_agent.py:42–65`, `insider_agent.py:17`, `short_interest_agent.py:17` — Keine Exception-Guard auf Provider-Response
`quality_agent.py` hat `if isinstance(data, Exception): data = {}`, aber diese drei Agents nicht — inkonsistentes Fehlerverhalten zwischen Geschwister-Agents.

### 45. `recommendation.py:91` — Market-String wird nicht normalisiert
`FULL_ANALYSIS_MARKETS = {"USA", "EU", "CH"}` — Case-sensitive Membership-Check. Wenn `market` als `"us"`, `"usa"`, oder `"United States"` übergeben wird, ist `full_analysis = False` und SHORT wird nie empfohlen.

### 46. `adapters/memory/supabase_memory.py:44` — Breites `AttributeError: pass` schluckt alle Fehler still
Jede Umbenennung von `CockpitResult`-Unterfeldern führt zu einem still leeren Snapshot ohne Fehlermeldung.

### 47. `agents/stock_deep_dive/equity_chief_agent.py`, `bond_chief_agent.py`, `commodity_chief_agent_mikro.py` — Chief Agents berechnen kein aggregiertes Signal
Alle drei Chief Agents sammeln Sub-Agent-Ergebnisse, synthetisieren aber nie ein Gesamt-Signal. Downstream-Consumer müssen die Aggregation selbst reimplementieren.

---

## README vs. Code-Diskrepanzen

| Behauptung im README | Realität im Code |
|---|---|
| **Buffett-Indikator** als Kern-Makro-Metrik aufgeführt | Null Implementierung — kein Agent, keine FRED-Series, kein Modellfeld |
| **Big Mac Index** als Bewertungsmethode aufgeführt | Null Implementierung im gesamten Codebase |
| **Redis** als Event Bus | `redis_bus.py` enthält `InMemoryEventBus`; Redis ist in einem auskommentierten TODO |
| **Finnhub** als Live-Datenquelle | Alle Methoden werfen `NotImplementedError` |
| **ECB/SNB** als Live-Datenquellen | `ecb_snb_stub.py` — jede Methode gibt `None` zurück mit TODO-Kommentar |
| **Shiller CAPE** als funktionierende Metrik | Alle Ticker hartcodiert als `None` mit TODO |
| **Fear & Greed Index** als aktiver Feed | `return None` hartcodiert mit TODO |
| **COT Agent** beschrieben als funktionierend | Gibt immer Default-NEUTRAL-Stub zurück |
| **Windows Task Scheduler** für Background-Runner | Keine `.bat`, `.xml` oder Scheduler-Konfiguration im Repo |

---

## requirements.txt-Lücken

| Package | Status |
|---|---|
| `anthropic` | **FEHLT** — genutzt in `claude_adapter.py`, wird von `pip install -r requirements.txt` nicht installiert |
| `python-dotenv` | **FEHLT** — genutzt in `background_runner.py` und `config/settings.py` |
| `plotly` | Aufgeführt aber im aktiven Code ungenutzt (nur Archiv) |
| `redis` | Nicht aufgeführt (konsistent mit Code, inkonsistent mit README) |
| `finnhub-python` | Nicht aufgeführt (Import auskommentiert) |

**Lösung:** `anthropic` an den Anfang von `requirements.txt` ergänzt. Zusätzlich `requests` hinzugefügt, das für die FMP API (Bug #3 / Shiller KGV EU/CH) benötigt wird. `python-dotenv` war bereits vorhanden.

---

## Test-Lücken

- **`RegimeDetector`** — Keine Tests. Die gewichtete Scoring- und Schwellenwert-Logik, die jede Empfehlung antreibt, ist vollständig ungetestet.
- **`MoatAgent` LLM-Parse-Logik** — `_overall()`-Schwellenwerte, Score-Clamping, JSON-Parsing — ungetestet.
- **`ValuationRangeAgent`-Mathematik** — DCF, KGV-Multiple, EV/EBITDA-Formeln — ungetestet.
- **`FundamentalsAgent._score()`** — 7-Indikator-Scoring-Funktion — ungetestet.
- **Chief-Agent-Tests** — Verifizieren nur `isinstance(result, XxxResult)` und `bus.publish.assert_called_once()`. Keine Logik, Fallback-Korrektheit oder Aggregation wird geprüft.
- **Backtester-Kontext-Einfluss auf Confidence** — `compute_confidence` hat `backtester_context`-Parameter der in `test_confidence.py` nie mit Wert exercised wird.

---

## Gesamtübersicht nach Priorität

| Priorität | Anzahl | Wichtigste Beispiele |
|---|---|---|
| **Crash / Datenverlust** | 8 | Fehlende BottomUpResult-Args, falscher JudgmentOrchestrator-Aufruf, Anomalie-Schweregrade immer "none", Connection Leak |
| **High Severity** | 17 | Regime-Schwellenwerte falsch, SHORT-Bias durch "contradicting", ungültige Ticker, Sektor Leading/Lagging nach Preis |
| **Medium Severity** | 22 | Falsy-Zero-Bugs, tote Exception-Guards, Population-Varianz, EXPANSION als Default-Regime |
| **README vs. Code** | 9 | Buffett-Indikator, Big Mac Index, Redis, Finnhub, ECB/SNB — alle behauptet aber fehlend/gestubbt |
| **requirements.txt** | 2 | `anthropic` und `python-dotenv` fehlen |
| **Test-Lücken** | 6 | RegimeDetector, MoatAgent, ValuationRange-Mathematik vollständig ungetestet |

---

## Empfohlene Fix-Reihenfolge

1. **`adapters/cache/result_cache.py:233`** — `index` und `commodity_deep` in `BottomUpResult()`-Konstruktor ergänzen
2. **`app/main.py:130`** — `memory`-Argument an `JudgmentOrchestrator` übergeben
3. **`core/domain/regime.py:17–23`** — Schwellenwert-Reihenfolge von `RECOVERY`/`SLOWDOWN` korrigieren
4. **`core/domain/recommendation.py:92`** — `"contradicting"` aus der Bearish-Bedingung entfernen
5. **`adapters/memory/supabase_memory.py:128–129`** — Echte Anomalie-Schweregrade aus `AnomalyReport` schreiben
6. **`adapters/memory/supabase_memory.py`** — Verbindungen explizit schliessen (`conn.close()` in finally-Block)
7. ~~**`core/domain/regime.py:7`** — Inflation-Lambda-Logik korrigieren (Dead Code-Zweig + Lücke 3–4%)~~ ✅ Zusammen mit Bug #3 erledigt
8. **`requirements.txt`** — `anthropic` und `python-dotenv` ergänzen
9. **`adapters/data/finnhub.py`** — Echte Implementierung oder klare NotImplemented-Behandlung im Orchestrator
10. ~~**Ungültige Ticker** (`^PCALL`, `ZNC=F`, `NI=F`) ersetzen oder als Stub markieren~~ ✅ Gelöst: `ZNC=F` und `NI=F` durch echte FMP-Calls ersetzt (`/v3/quote/ZINC`, `/v3/quote/NICKEL`) — Zink und Nickel sind LME-Kontrakte ohne Yahoo-Finance-Äquivalent. `^PCALL` durch direkten CBOE-CSV-Fetch ersetzt: die Funktion `_fetch_cboe_put_call()` lädt täglich die CBOE-Statistikdatei und liest die "TOTAL PUT/CALL RATIO"-Spalte aus, mit Fallback auf bis zu 5 Tage zurück für Wochenenden und Feiertage. Der tote `isinstance(ratio, Exception)`-Guard wurde ebenfalls entfernt.
11. ~~**`agents/market_cockpit/sector/sector_performance_agent.py`** — Performance als prozentuale Rendite statt absoluter Preis berechnen~~ ✅ Gelöst: `get_current_price` durch `get_price_history(ticker, "1mo")` ersetzt. Neue `_pct_return()`-Hilfsfunktion berechnet die 1-Monats-Rendite `(last - first) / first * 100`. `leading`/`lagging` werden jetzt korrekt nach prozentualer Rendite bestimmt, nicht nach absolutem ETF-Preis.
12. ~~**`adapters/event_bus/redis_bus.py`** — Handler-Exceptions per try/except isolieren~~ ✅ Gelöst: Jeden `handler(event)`-Aufruf in `try/except` eingewickelt. Ein fehlerhafter Handler loggt den Fehler via `logging.exception` und überspringt — alle nachfolgenden Handler erhalten das Event trotzdem.
13. ~~**Alle Falsy-Zero-Bugs** — `if x and y` durch `if x is not None and y is not None` ersetzen~~ ✅ Gelöst in 6 Dateien (11 Stellen): `interest_rate_agent.py` (Zeile 62 + `or 0`-History-Appends), `yield_spread_agent.py`, `precious_metals_macro_agent.py`, `bond_metrics_agent.py`, `bond_duration_agent.py`, `cross_metal_agent.py`, `index_earnings_agent.py`, `index_valuation_range_agent.py`, `valuation_range_agent.py`. Alle `if x and y` → `if x is not None and y is not None`. `fed_rate or 0`-Appends in der Rate-History durch explizite `if x is not None`-Guards ersetzt, damit ein fehlgeschlagener API-Call die Richtungsbestimmung nicht vergiftet.
14. ~~**README aktualisieren**~~ ✅ Laufend aktualisiert — Buffett-Indikator implementiert, Big Mac Index folgt als nächstes.

### Implementierungen (neue Features)

#### Buffett-Indikator ✅ (global, ~150 Länder, Z-Score-basiert)

**Datenquellen:**
- **USA** — FRED (`WILL5000INDFC` / `GDP`): Echtzeit, monatlich aktualisiert. Zusätzlich 10 Jahre Quartalshistorie via `get_buffett_history()` für Z-Score-Berechnung.
- **Alle anderen Länder** — Weltbank API (`CM.MKT.LCAP.GD.ZS`, `mrv=15`): Ein einziger HTTP-Call liefert 15 Jahreswerte pro Land für ~150 Länder. Kein API-Key nötig.

**Modell:**
```python
@dataclass
class BuffettCountryPoint:
    ratio_pct: Optional[float]   # aktueller Wert Marktkapitalisierung / BIP * 100
    signal: Signal               # BULLISH <75% / BEARISH >135% (informativer Label, kein Entscheidungssignal)
    year: Optional[int]          # None = FRED Echtzeit; int = Weltbank-Jahreswert
    z_score: Optional[float]     # aktuell vs. eigene 10J-Geschichte (mind. 8 Datenpunkte nötig)

@dataclass
class BuffettIndicatorSnapshot:
    countries: dict[str, BuffettCountryPoint]  # ISO-3 → Daten
    signal: Signal               # USA-Signal (für Regime-Verwendung)
    global_median: Optional[float]  # Median aller Länder (für Dashboard)
```

**Z-Score pro Land:** Jedes Land vergleicht seinen aktuellen Wert mit der **eigenen** historischen Basis — nicht mit einem universellen US-Schwellenwert. Z-Score Deutschland ≠ Z-Score Italien, weil beide strukturell unterschiedliche Marktkapitalisierungen relativ zu ihrem BIP haben.

**Top-Down-Kontext (`top_down_context.py`):**
- Neuer `market`-Parameter (`derive_top_down_context(..., market="FR")`)
- Neuer `asset_class`-Parameter — Buffett erscheint **nur** bei `equity`, `etf`, `index`; nicht bei `bond`, `commodity`, `precious_metal`
- Zeigt nur das analysierte Land, nicht alle 150
- Erscheint nur wenn |Z-Score| ≥ 1.5 (statistisch auffällig) — im Normalbereich kein Hinweis
- Fallback auf absolute Schwellen (75%/135%) wenn <8 historische Datenpunkte

**Anomalie-Agent (`top_down_anomaly_agent.py`):**
- Keine harte 200%-Schwelle mehr
- Liest `countries["USA"].z_score` aus dem Snapshot (vorberechnet vom Agent)
- Wird nur ausgelöst wenn |Z-Score| > `Z_THRESHOLD` (gleiche Logik wie VIX, CPI, Yield Spread)
- Buffett-Check übersprungen wenn `asset_class` nicht `equity`/`etf`/`index`

**Systemweite EU-Bereinigung:**
- `EU` als Markt-Code existiert nicht mehr — es gibt keine Eurozone-Aktie
- `FULL_ANALYSIS_MARKETS` hat alle 19 Eurozone-Länder einzeln (ISO-2): `DE, FR, IT, ES, NL, AT, BE, PT, FI, IE, GR, SK, SI, EE, LV, LT, LU, MT, CY`
- `FULL_ANALYSIS_MARKETS` ist jetzt nur in `recommendation.py` definiert (war dupliziert in `judgment_orchestrator.py`)
- `_MARKET_COUNTRY` in `top_down_context.py` unterstützt ISO-2, ISO-3 und System-Kürzel
- Nutzung: `python -m app.main judge ENI.MI IT` statt `... EU`

**Integration:** `MacroChiefResult.buffett_indicator`, paralleler Lauf in `MacroChiefAgent`, `BuffettIndicatorReady`-Event in `events.py`, `get_buffett_data()` + `get_buffett_history()` in `MacroDataProvider`-Port und `FredDataProvider`.

---

## Offene Ausbau-Ideen (aus Diskussion entstanden)

### A. Regime-Backtester: Selbstlernende Validierung
Der `BacktesterChiefAgent` prüft bereits vergangene Empfehlungen. Sinnvoller nächster Schritt:
Den **Composite-Score und das erkannte Regime** zusammen mit dem Datum speichern.
Nach z.B. 3 Monaten prüfen: Hat das damalig erkannte Regime (z.B. ABSCHWUNG) tatsächlich
zu den erwarteten Marktbedingungen geführt? Falls nicht → Gewichte in `INDICATOR_WEIGHTS`
oder Schwellenwerte in `_regime_from` automatisch oder manuell anpassen.
Das wäre echter Lernkreislauf: Vorhersage → Realität → Kalibrierung.
