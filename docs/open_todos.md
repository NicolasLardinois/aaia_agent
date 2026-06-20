# Open TODOs

Alle offenen Aufgaben aus Codebase, Code Review (2026-06-05) und Plan-Dateien.
Stand: 2026-06-19 | Nach Erledigung: Zeile abhaken oder entfernen.

> **Hinweis (2026-06-19):** Die fachliche Review `docs/finanz_konzept_review_2026-06-16.md` (~50 Befunde) wurde gegen den Code abgeglichen — **Ergebnis: weitgehend umgesetzt.** Der Status steht in **§10**; offene Reste sind dort verlinkt und in §1–§7 bereits erfasst.

---

## GESAMTÜBERSICHT

> **Details und Stand: siehe die Abschnitte unten.** Maßgeblich sind die Häkchen
> (`- [ ]` offen / `- [x]` erledigt) direkt an den Einträgen — bewusst **keine**
> separat gepflegte Anzahl, die ohnehin veraltet.

| Bereich |
|---------|
| Offene Bugs (code_review_2026-06-05.md) |
| Stub-APIs (ECB, SNB, etc.) |
| Agent-Stubs (komplette Implementierung fehlt) |
| Fehlende Einzelfeatures in bestehenden Agents |
| Feature-Backlog (Pläne) |
| Test-Lücken |
| Code-Qualität / toter Code |
| Design-Entscheidungen (Frontend) |

---

## 1. OFFENE BUGS (aus code_review_2026-06-05.md)

> **Audit 2026-06-20 (Subagenten, gegen den Code auf `master`):** Die 12 Bugs einzeln verifiziert.
> **7 echt behoben** (hier abgehakt, mit Code-Beleg): #1, #2, #4, #5, #26, #34, #36.
> **5 verbleiben** (#30, #42, #44, #46, #47) — Abarbeitung **eine PR pro Bug** (Start #44); die präzise
> Rest-Scope-Analyse aus dem Audit kommt jeweils in die zugehörige Fix-PR (mit `[x]` + Lösung).
> Hinweis: Die Zeilennummern in den Bug-Texten sind veraltet (Code hat sich verschoben); maßgeblich ist der Beleg im Audit-Vermerk.

### Kritisch (Crash / Datenverlust)

- [x] **Bug #1** — `adapters/cache/result_cache.py:233`
  `BottomUpResult` braucht 13 Felder; `load_bottom_up()` übergibt nur 11 — `index` und `commodity_deep` fehlen.
  Raises `TypeError` jedes Mal wenn eine frische Bottom-Up-Cache-Datei existiert (normaler Happy Path).
  **Lösung:** Die zwei fehlenden Felder analog zu den anderen 11 aus JSON lesen und übergeben.
  **✅ Audit 2026-06-20 BEHOBEN:** `result_cache.py:902-903` übergibt heute `index=_load_index_result(...)` + `commodity_deep=_load_commodity_deep(...)` — alle 13 Felder vollständig, Save/Load symmetrisch. *(Offen bleibt nur ein fehlender Round-Trip-Regressionstest.)*

- [x] **Bug #2** — `app/main.py:130`
  `JudgmentOrchestrator(llm, bus)` — fehlt `memory` als drittes Argument.
  Crasht sofort im `judge`-Modus. Das `memory`-Objekt ist weiter oben bereits instanziert.
  **✅ Audit 2026-06-20 BEHOBEN:** `app/main.py` ruft `JudgmentOrchestrator(llm, bus, memory)`; Signatur `__init__(self, llm, bus, memory)` (`orchestrators/judgment_orchestrator.py:19`) passt. *(Kein Konstruktor-Smoke-Test vorhanden.)*

- [x] **Bug #4** — `adapters/memory/supabase_memory.py:128-129`
  Anomalie-Schweregrade sind hartcodiert auf `"none"` — die echten `AnomalyReport.severity`-Werte werden nie in die DB geschrieben.
  Jede Datenbankzeile ist permanent korrumpiert.
  **Lösung:** `result.top_down_anomaly.severity if result.top_down_anomaly else "none"` (analog bottom_up).
  **✅ Audit 2026-06-20 BEHOBEN:** `supabase_memory.py:147-148` liest `top_down_anomaly.severity`/`bottom_up_anomaly.severity` korrekt aus, `"none"` nur als None-Fallback.

- [x] **Bug #5** — `adapters/memory/supabase_memory.py`
  `psycopg2.connect()` wird in jeder Methode geöffnet, nie geschlossen → Connection Pool Leak.
  **Lösung:** `_connect()` als `@contextmanager` mit `conn.close()` in `finally`-Block.
  **✅ Audit 2026-06-20 BEHOBEN:** `_connect()` ist `@contextmanager` mit `conn.close()` im `finally` (`supabase_memory.py:57-82`, inkl. 3×-Retry); alle 7 Methoden nutzen `with self._connect() as conn`.

### Medium Severity

- [x] **Bug #26** — `agents/market_cockpit/macro/shiller_cape_agent.py:29`
  Kein unterer Schwellenwert für BULLISH — jeder CAPE-Wert unterhalb des Durchschnitts, egal wie weit, erzeugt BULLISH.
  Ein Markt im Kollaps erzeugt dasselbe Signal wie einer, der leicht unterbewertet ist.
  **✅ Audit 2026-06-20 BEHOBEN (durch Umbau):** Der Agent existiert nicht mehr; CAPE ist heute eine reine Mathe-Funktion ohne Signal (`core/utils/valuation_math.py:101`). Das Nachfolge-Signal in `index_valuation_agent.py` ist **beidseitig** begrenzt (ERP-Cutoffs + symmetrischer PE-Puffer) und durch `test_index_valuation_agent.py` (`test_signal_buffers_are_symmetric` u.a.) abgesichert.

- [ ] **Bug #30** — `agents/market_cockpit/macro_chief_agent.py:82`
  `EXPANSION` als Default-Regime wenn alle Provider ausfallen.
  Nachgelagerte Agenten generieren aktionabel wirkende "buy Tech" Empfehlungen ohne reale Datenbasis.
  **Lösung:** Default auf `NEUTRAL` oder `UNKNOWN` setzen.

- [x] **Bug #34** — `agents/stock_deep_dive/bond/bond_metrics_agent.py:47`
  `if ytm and inflation` schlägt für Zero-Coupon-Anleihen (`ytm=0.0`) fehl.
  Real-Yield wird `None` statt `-inflation`, versteckt genuinen negativen Real-Yield.
  **Lösung:** `if ytm is not None and inflation is not None`.
  **✅ Audit 2026-06-20 BEHOBEN:** `bond_metrics_agent.py:90` nutzt `if ytw is not None and infl is not None` (Real-Yield aus YTW); `crate is not None` lässt Zero-Coupon korrekt durch — `0.0` wird nicht mehr fälschlich als `None` behandelt.

- [x] **Bug #36** — `agents/stock_deep_dive/commodity/supply_demand_agent.py:77`
  `_signal()` ist definiert aber wird nie aufgerufen. `signal=Signal.NEUTRAL` ist hartcodiert.
  Gesamte Signallogik ist toter Code.
  **✅ Audit 2026-06-20 BEHOBEN:** `supply_demand_agent.py:75` ruft `signal=_signal(pct)` im AVAILABLE-Zweig real auf; hartes NEUTRAL nur noch im legitimen `_DEFAULT`/UNAVAILABLE-Pfad (kein Provider/keine Daten). Tests (`test_low/high/normal_inventory`, `test_run_available_with_inventory`) beweisen echtes BULLISH.

- [ ] **Bug #42** — `agents/stock_deep_dive/index/index_price_agent.py:61-62`
  `close.index.searchsorted(f"{datetime.utcnow().year}-01-01")` wirft `TypeError` bei timezone-aware Index.
  Ausserdem: wenn Jahresanfang nicht im 5-Jahres-Fenster liegt, wird YTD falsch berechnet.

- [ ] **Bug #44** — `agents/stock_deep_dive/equity/fundamentals_agent.py`, `insider_agent.py`, `short_interest_agent.py`
  Keine Exception-Guard auf Provider-Response (kein `if isinstance(data, Exception)`).
  Inkonsistent mit `quality_agent.py` (hat den Guard). Exceptions propagieren unkontrolliert.

- [ ] **Bug #46** — `adapters/memory/supabase_memory.py:44`
  Breites `except AttributeError: pass` schluckt alle Fehler still.
  Jede Umbenennung von `CockpitResult`-Unterfeldern führt zu einem leeren Snapshot ohne Fehlermeldung.

- [ ] **Bug #47** — `agents/stock_deep_dive/equity_chief_agent.py`, `bond_chief_agent.py`, `commodity_chief_agent_mikro.py`
  Chief Agents sammeln Sub-Agent-Ergebnisse, synthetisieren aber kein aggregiertes Gesamt-Signal.
  Downstream-Consumer müssen die Aggregation selbst reimplementieren.
  *(Teilweise durch ChiefAgents-Plan adressiert — `docs/superpowers/plans/2026-06-04-chief-agents.md`)*

---

## 2. STUB-APIS — DATENQUELLEN NICHT ANGEBUNDEN

### adapters/data/ecb_snb_stub.py

ECB (`EcbStubProvider`) — alle geben `None` zurück:
- [ ] `get_interest_rate()` — Quelle: ECB SDW
- [ ] `get_m3_growth()` — Quelle: ECB SDW
- [ ] `get_balance_sheet_growth()` — Quelle: ECB SDW
- [ ] `get_cpi()` — Quelle: Eurostat
- [ ] `get_core_cpi()` — Quelle: Eurostat
- [ ] `get_ppi()` — Quelle: Eurostat
- [ ] `get_gdp_growth()` — Quelle: Eurostat
- [ ] `get_unemployment()` — Quelle: Eurostat
- [ ] `get_pmi()` — Quelle: S&P Global
- [ ] `get_m2_growth()` — Quelle: ECB SDW
- [ ] `get_sovereign_yields()` — Quelle: ECB SDW (DE, IT, FR, ES 10Y)

SNB (`SnbStubProvider`) — alle geben `None` zurück:
- [ ] `get_interest_rate()` — Quelle: data.snb.ch
- [ ] `get_m3_growth()` — Quelle: data.snb.ch
- [ ] `get_balance_sheet_growth()` — Quelle: data.snb.ch
- [ ] `get_cpi()` — Quelle: BFS
- [ ] `get_core_cpi()` — Quelle: BFS
- [ ] `get_gdp_growth()` — Quelle: SECO
- [ ] `get_unemployment()` — Quelle: SECO
- [ ] `get_m2_growth()` — Quelle: data.snb.ch
- [ ] `get_sovereign_yield_10y()` — Quelle: Yahoo Finance / SNB
- [ ] `get_sovereign_yield_2y()` — Quelle: Yahoo Finance / SNB

### adapters/event_bus/redis_bus.py (Zeile 36)
- [ ] Redis-Implementierung für Produktion
  Klasse ist auskommentiert, wirft `NotImplementedError`. Aktuell läuft alles über `InMemoryEventBus`.

### Bond-Datenquelle (`get_bond_data()` → `{}`) — Eingaben für die Fixed-Income-Engine *(aus Plan C)*

- [ ] **Echte Anleihe-Rohdaten anbinden.**
  Die Bond-Rechenmaschine (`core/utils/bond_math.py`, `core/utils/credit.py`) ist fertig und getestet, aber `MarketDataProvider.get_bond_data()` liefert real `{}` → die Bond-Agenten haben keine Eingaben und geben korrekt `None`/NEUTRAL aus (statt falscher Zahlen).
  Benötigte Roh-Bausteine: Clean-Preis (%-Kurs), `coupon_rate`, `frequency`, `maturity_years`, optional `accrued_interest`, `call_price`/`years_to_call`, `is_callable`/`is_putable`, Ratings (S&P/Moody's/Fitch), `recovery_rate`, ggf. Spread-/Kurvendaten, `breakeven_inflation`.
  **Ansatz:** Bond-Datenadapter implementieren (z. B. Finnhub/FMP-Bond-Endpunkte oder andere Anleihe-API) und `get_bond_data(ticker)` befüllen; Einheiten-/Clean-Konvention wie in der Engine dokumentiert. Erst dann produzieren die Bond-Agenten echte Kennzahlen.

---

## 3. AGENT-STUBS — KOMPLETTE IMPLEMENTIERUNGEN AUSSTEHEND

- [ ] **`agents/stock_deep_dive/index/index_breadth_agent.py` (Zeile 14)**
  Gibt nur Default-Werte zurück. Benötigt Preisdaten aller Index-Komponenten.
  Quellen: FRED (SPSICOMP), StockCharts, Bloomberg Terminal.

- [ ] **`agents/stock_deep_dive/commodity/cot_agent.py` (Zeile 11)**
  CFTC Commitment of Traders Report. Format: CSV, wöchentlich.
  Signallogik: KONTRÄR — Spekulanten liegen am Extrempunkt oft falsch.
  Quelle: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

- [ ] **`agents/stock_deep_dive/commodity/supply_demand_agent.py` (Zeile 61)**
  EIA API (Öl/Gas), USDA (Agrar), LME (Metalle) nicht angebunden.

- [ ] **`agents/market_cockpit/sentiment/fear_greed_agent.py` (Zeile 28)**
  CNN Fear & Greed API nicht angebunden. Gibt immer `None` zurück.

- [ ] **`agents/stock_deep_dive/equity/valuation_range_agent.py` (Zeile 55)**
  Vollständige Implementierung wartet auf Finnhub/FMP Adapter.

---

## 4. FEHLENDE EINZELFEATURES IN BESTEHENDEN AGENTS

### agents/market_cockpit/macro/inflation_agent.py

- [ ] **CPI Trend-Analyse** (`_signal()`, Parameter `trend` — reserviert, Zeile 20)
  `trend="rising"` soll Signal verschärfen, `trend="falling"` mildern.
  Benötigt: neue Provider-Methode `get_cpi_history(months=6)`.

- [ ] **USA Core CPI** (`InflationDataPoint.core_cpi` für USA ist `None`, Zeile 81)
  Quelle: FRED `CPILFESL` via `extended_state`.

- [ ] **USA PCE** (`InflationDataPoint.pce` für USA ist `None`, Zeile 82)
  Quelle: FRED `PCEPI`. Wichtig: Fed-Ziel bezieht sich auf PCE, nicht CPI.

- [ ] **Eurozone Real Rate 10Y** (`InflationDataPoint.real_rate_10y` für EU ist `None`)
  Berechnung: EZB 10Y-Rendite minus EZB CPI.

- [ ] **Schweiz PPI** (`InflationDataPoint.ppi` für CH ist `None`)
  Quelle: SNB / BFS Erzeugerpreisindex.

### agents/market_cockpit/macro/interest_rate_agent.py (Zeile 77)
- [ ] **FRED WALCL** — Fed Balance Sheet Growth (`balance_sheet_growth=None`)

### agents/market_cockpit/macro/gdp_agent.py (Zeilen 58, 70)
- [ ] **ISM Manufacturing PMI** für USA (`pmi=None`) — Quelle: FRED / ISM
- [ ] **procure.ch PMI** für Schweiz (`pmi=None`)

### agents/market_cockpit/macro/credit_agent.py (Zeilen 38–39)
- [ ] EU-Kreditwachstum via ECB API (aktuell immer NEUTRAL)
- [ ] CH-Kreditwachstum via SNB API (aktuell immer NEUTRAL)

### agents/market_cockpit/macro/labor_income_agent.py (Zeilen 38–39)
- [ ] EU-Löhne via Eurostat / ECB API (aktuell immer NEUTRAL)
- [ ] CH-Löhne via SNB API (aktuell immer NEUTRAL)

### agents/stock_deep_dive/precious_metals/precious_metal_price_agent.py (Zeilen 44–54)
- [ ] RSI und MA50/MA200 aus Preishistorie berechnen
- [ ] Performance 1W/1M/3M/1Y/5Y aus Preishistorie
- [ ] Korrelation mit Realzins (`real_yield_correlation=None`)
- [ ] Signal aus Momentum ableiten (aktuell immer `Signal.NEUTRAL`)

### agents/stock_deep_dive/index/sector_composition_agent.py (Zeilen 40, 57)
- [ ] ETF-Holdings via echte APIs (iShares, SPDR) — aktuell hard-coded (~2025, braucht manuelle Updates)
- [ ] `top_10_concentration` berechnen (aktuell `None`)

### agents/stock_deep_dive/index/index_valuation_agent.py (Zeile 59)
- [x] Shiller CAPE — **implementiert** (2026-06-19 verifiziert): `earnings_yield`/`equity_risk_premium`/`shiller_cape` im Agenten, zinsabhängiges ERP-Signal.
  Offen ist nur noch die **Datenquelle 10J-Real-EPS** (FMP) anzubinden, damit `cape` real befüllt wird statt `None` → siehe §2 (Datenadapter).

### agents/stock_deep_dive/commodity/commodity_valuation_range_agent.py (Zeile 64)
- [ ] Commodity-spezifische Kostenmodelle (`production_cost_low/high=None`)

### core/domain/recommendation.py (Zeile 67–79) — Konfidenz-Kalibrierung befüllen *(aus Plan A, P1.3)*

- [ ] **Backtest-Buckets für `compute_confidence` produzieren & durchreichen**
  Der String-Key-Lookup `calibration["alignment:severity"]` ist eingebaut und getestet, aber **kein Producer befüllt die Buckets** → in Produktion derzeit immer Fallback `base = 0.70` (Verhalten wie vor Plan A).
  **Lösungsansatz (so würde ich es angehen):**
  1. **History anreichern:** `alignment` und `severity` je abgeschlossenem Trade zusätzlich in der History speichern (`adapters/memory/supabase_memory.py` → `save_global_history` + Schema-Spalte), damit Buckets überhaupt bildbar sind.
  2. **Buckets berechnen:** Im Backtester (z. B. `backtester_chief_agent` oder ein eigener Kalibrierungs-Schritt) je `(alignment, severity)` aus den abgeschlossenen Forward-Windows die historische Trefferquote + Stichprobengröße ermitteln → Dict mit **String-Keys** `{"aligned_bullish:none": {"hit_rate": 0.71, "n": 18}, ...}` (JSON-serialisierbar).
  3. **Durchreichen:** Dieses Dict im Backtester-Report (`save_backtester_report`) ablegen und über `backtester_context["calibration"]` an `judgment_agent` → `compute_confidence(..., calibration=…)` weitergeben.
  4. **Aktivierung:** Greift automatisch ab `n >= _CALIB_MIN_N` (=10) pro Bucket (bereits implementiert); darunter bleibt der Fallback 0.70.

---

## 5. FEATURE-BACKLOG (aus Plan-Dateien)

### Agricultural Investment Signal
- [ ] 4 Tasks — `docs/superpowers/plans/2026-06-15-agricultural-investment-signal.md`
  Wenn agricultural BEARISH → Hinweis auf Rohstoff-ETFs (DBA, WEAT, CORN, SOYB).

### Big Mac Index
- [ ] 5 Tasks — `docs/superpowers/plans/2026-06-08-big-mac-index.md`
  Adjustierter Big Mac Index für ~50 Länder (Economist GitHub CSV).

### ChiefAgents-Refactoring
- [ ] 12 Tasks — `docs/superpowers/plans/2026-06-04-chief-agents.md`
  3-schichtige Architektur: Orchestratoren → ChiefAgents → SubAgents, parallel + fehlertolerant.

### Confidence + Memory + Backtester + XAI + Portfolio
- [ ] 11 Tasks — `docs/superpowers/plans/2026-06-04-confidence-memory-backtester-xai.md`
  Anomalieerkennung, dynamische Konfidenz, Supabase-Memory, tägliche Backtester-Läufe.

### Regime-Backtester: Selbstlernende Validierung (Ausbau-Idee aus code_review)
- [ ] Composite-Score + erkanntes Regime mit Datum speichern.
  Nach 3 Monaten prüfen ob das damalige Regime tatsächlich eingetreten ist.
  Falls nicht: Gewichte in `INDICATOR_WEIGHTS` oder Schwellenwerte in `_regime_from` anpassen.
  Echter Lernkreislauf: Vorhersage → Realität → Kalibrierung.

---

## 6. TEST-LÜCKEN

- [ ] **RegimeDetector** — vollständig ungetestet (Scoring-Logik treibt jede Empfehlung an)
- [ ] **MoatAgent** — `_overall()`-Schwellenwerte, Score-Clamping, JSON-Parsing ungetestet
- [ ] **ValuationRangeAgent** — DCF, KGV-Multiple, EV/EBITDA-Formeln ungetestet
- [ ] **FundamentalsAgent** — `_score()` mit 7 Indikatoren ungetestet
- [ ] **Chief-Agent-Tests** — prüfen nur `isinstance(result, XxxResult)`, keine Logik oder Aggregation
- [ ] **BacktesterChiefAgent** — `backtester_context`-Einfluss auf Confidence nie getestet

---

## 7. CODE-QUALITÄT / TOTER CODE

- [x] **DB-Schema ins Repo (`db/schema.sql`).** Am 2026-06-20 angelegt und noch am selben Tag **autoritativ** ersetzt (echte Typen/PKs/Defaults aus `information_schema`/`pg_indexes` der laufenden Supabase-DB; *direkt auf `master`, bewusste Workflow-Ausnahme*). Lösung: 3 Tabellen (`analysis_memory`/`backtester_reports`/`portfolio_snapshots`), `id uuid DEFAULT gen_random_uuid()`, `timestamp timestamptz`, JSONB-Felder mit Defaults; `short_action` enthalten.
- [ ] **Fehlende Lese-Indizes (Performance).** In der DB existieren nur die PK-Indizes (auf `id`). Die Lese-Filter haben **keine** Indizes: `analysis_memory (ticker, timestamp)` (`load_history`) und `backtester_reports (backtester_type, timestamp)` (`load_latest_backtester_report`). **Ansatz:** je einen Index anlegen, z. B. `CREATE INDEX idx_analysis_memory_ticker_ts ON analysis_memory (ticker, timestamp DESC);` — und in `db/schema.sql` nachziehen. Niedrige Prio, solange die Tabellen klein sind.
- [ ] **Echtes Migrations-Tool/-Ordner** statt der manuell gepflegten Migrationshistorie am Dateiende von `db/schema.sql` (z. B. nummerierte `db/migrations/*.sql`). Niedrige Prio.
- [ ] `core/utils/statistics.py` (Zeile 4) — `Z_THRESHOLD = 2.5` wird nirgends verwendet; entfernen oder einbinden
- [ ] `tests/test_recommendation.py` (Zeile 6) — `_short_report()` definiert aber nie aufgerufen; entfernen
- [ ] `docs/code_review_2026-06-05.md` — Bug-Fixes Tasks 1–18 als ✅ markieren (alle abgeschlossen, Datei spiegelt das nicht wider)

### Aus Plan 0 (Review 2026-06-16 — bewusst zurückgestellte Minor-Robustheit, niedrige Prio)

- [ ] `core/utils/relative.py` `_winsorize` — kein Guard bei `fraction >= 0.5`: dann gilt `lo_idx >= hi_idx` und alle Werte kollabieren still auf einen einzigen Wert.
  **Ansatz:** entweder `if fraction >= 0.5: raise ValueError(...)` oder Docstring-Constraint „nur `fraction < 0.5` sinnvoll" + früher Return. Aufrufer nutzen 0.05–0.1 → derzeit kein realer Schaden.
- [ ] `adapters/persistence/json_dated_history.py` (`JsonDatedHistory`, JSON-Adapter von `DatedHistoryPort`) — JSON-Leaf-Werte werden nicht typvalidiert: ein manuell korrumpiertes `{"series": {"2026-01-01": "text"}}` liefert `(date, str)` statt `(date, float)`; der Fehler explodiert erst beim Aufrufer.
  **Ansatz:** in `values()` `float(v)` casten (und unparsebare Einträge überspringen) oder beim `_load()` validieren; alternativ Docstring-Hinweis „Werte müssen float sein".
- [ ] `core/utils/statistics.py` — Datei trägt zwei Verantwortlichkeiten (klassisch `z_score`/`compute_severity` vs. robust `robust_z_score`/`bonferroni_z_threshold`).
  **Ansatz:** *nur bei weiterem Wachstum* Split in z. B. `statistics_robust.py` erwägen. Aktuell (≈60 Zeilen) keine Aktion nötig.

### Aus Plan B (Review 2026-06-16 — bewusst zurückgestellt, niedrige Prio)

- [ ] `core/utils/valuation_math.py` `real_rate_anchor` — bei extremem Realzins (z. B. Gold bei real_rate ~10 %) wird `fair = max(0, intercept + slope*rate) = 0` → Band degeneriert still zu `(0, 0)`, ohne dem Nutzer die „kein sinnvoller Anker"-Situation zu kommunizieren.
  **Ansatz:** entweder `None` (statt `(0,0)`) zurückgeben, wenn `fair <= 0`, und im Agenten die Methode dann überspringen (analog zu den `>0`-Guards bei EPS/EBITDA/FCF), oder ein explizites „nicht aussagekräftig"-Flag setzen. Niedrige Prio (nur bei sehr hohen Realzinsen relevant).

### Aus Plan C (Review 2026-06-16 — bewusst zurückgestellt)

- [ ] **Echte OAS-basierte Effective Duration für optionsbehaftete Bonds** (`agents/stock_deep_dive/bond/bond_duration_agent.py`).
  Derzeit numerische Näherung via Vanilla-`bond_price`-Shifts → für callable/putable Bonds ≈ Modified Duration (keine Optionsbereinigung, Optionswert unterschätzt). Label ist im Code als Näherung dokumentiert.
  **Ansatz:** einfaches Zinsmodell/Lattice (z. B. Binomial-/Trinomial-Baum) für die Optionsausübung implementieren; Effective Duration aus OAS-konsistenten Auf-/Abwärts-Preisen statt Vanilla-Shifts.
- [ ] **`BondMetricsSnapshot` um `ytw` (Yield-to-Worst) erweitern** *(Minor)*.
  YTW wird berechnet, aber nur im `*Ready`-Event-Payload transportiert (bewusste Plan-Design-Entscheidung: Zusatzgrößen via Events, Dataclasses unverändert). Downstream-Snapshot-Konsumenten müssen YTW aus Events rekonstruieren.
  **Ansatz:** falls Snapshot-Konsumenten YTW direkt brauchen, Feld `ytw: float | None = None` ergänzen und im Agenten befüllen.

### Aus Plan D1 (Review 2026-06-16/17 — Logik korrekt, Daten/Verdrahtung fehlt)

- [ ] **Yield-Curve Bull-Steepening-Signal verdrahten** (`agents/market_cockpit/yield_curve/yield_spread_agent.py`).
  Die Inversions-Lag-Logik (frisch invertiert→NEUTRAL, Bull-Steepening aus Inversion→BEARISH) ist implementiert, aber `run()` ruft `_point(..., prev_10y3m=None)` → der eigentliche Timing-BEARISH-Zweig **feuert nie**.
  **Ansatz:** vorherigen `usa_10y3m`-Wert über `JsonDatedHistory` persistieren (pro Lauf `append("usa_10y3m", heute, wert)`, dann `value_on_or_before` der Vorperiode) und als `prev_10y3m` übergeben.
- [ ] **Interest-Rate-Richtung verdrahten** (`agents/market_cockpit/macro/interest_rate_agent.py`).
  `_direction` nutzt korrekt `DatedHistoryPort`, aber `run()` übergibt `history=None` → immer `"stable"` → Signal immer NEUTRAL (auch EU/CH). Die restriktiv/expansiv-Signale tragen damit nichts zum Regime bei.
  **Ansatz:** je Region eine datierte Zinsreihe bereitstellen — entweder Provider liefert sie (in `InMemoryDatedHistory` umhüllen) oder `JsonDatedHistory` pro Lauf `append(series, heute, rate)`; an `_direction(..., history=…, series=…)` geben.
- [ ] **Money-Supply velocity-Modifikator** (`agents/market_cockpit/macro/money_supply_agent.py`) *(Minor)*.
  `_signal(excess, None)` — zweites Argument fest `None`; zudem Typ-Mismatch (`_signal` erwartet `'falling'`/`'rising'`, `velocity_m2` ist ein float). Der „Überschuss-Liquidität bei fallender Umlaufgeschwindigkeit → NEUTRAL"-Override greift nie.
  **Ansatz:** Velocity-Trend ableiten (aktuelle vs. vorherige Umlaufgeschwindigkeit, z. B. via DatedHistory) und als String an `_signal` geben.
- [ ] **EU/CH-Arbeitslosigkeit ins GDP-Signal** (`agents/market_cockpit/macro/gdp_agent.py`) *(Minor)*.
  Die Sahm-Regel braucht Arbeitslosen-Historie; für EU/CH liegt nur das aktuelle Niveau vor → Arbeitslosigkeit fließt dort nicht ins Signal (immer NEUTRAL, wenn nur Arbeitslosigkeit verfügbar).
  **Ansatz:** Arbeitslosen-Historie für EU/CH anbinden (Eurostat/SECO), damit Sahm rechnen kann; alternativ Niveau-basierter Fallback für Regionen ohne Historie.
- [ ] **Put/Call-Verlauf persistent statt I/O-intensiv** (`agents/market_cockpit/sentiment/put_call_agent.py`) *(Minor)*.
  `_fetch_cboe_put_call_history()` ruft pro Lauf N Tage einzeln ab (I/O-intensiv).
  **Ansatz:** durch persistente `JsonDatedHistory`-Anbindung ersetzen (täglicher Wert angehängt, z-Score gegen die gespeicherte Reihe) — passt zur Plan-E-Daten-Integration.
- [ ] **Buffett-Agent-Fallback länderspezifisch** (`agents/market_cockpit/macro/buffett_indicator_agent.py`) *(Minor)*.
  Ohne Landeshistorie fällt der Agent auf globale 75/135 % zurück; `core/domain/top_down_context.py` nutzt bereits länderspezifische Korridore (`_BUFFETT_CORRIDORS`).
  **Ansatz:** dieselben länderspezifischen Korridore auch im Agenten-Fallback verwenden (statt global 75/135).
- [ ] **Doppelte Testdatei** `tests/domain/test_top_down_context.py` vs. `tests/test_top_down_context.py` *(Minor, Aufräumen)* — auf einen Pfad konsolidieren.

### Aus Plan D2 (Review 2026-06-17 — Logik korrekt, Daten fehlt)

- [ ] **SUE in Produktion aktivieren: `get_earnings_history` um `actual`/`estimate` erweitern** (`adapters/data/finnhub.py`).
  Die SUE-Logik (`core/utils/scoring.py` `standardized_unexpected_earnings`) ist korrekt + getestet, aber der Adapter liefert pro Quartal nur `beat`/`revision`, **kein `actual`/`estimate`** → SUE gibt produktiv immer `None` zurück; `earnings_trend_agent` läuft dann nur über die Revisionen (die Magnitude-Komponente fehlt).
  **Ansatz:** im Adapter pro Quartal `actual` (EPS-Ist) und `estimate` (EPS-Schätzung) befüllen — yfinance liefert diese via `Ticker.get_earnings_dates()` als `epsActual`/`epsEstimate`. Reihenfolge **älteste-zuerst** beibehalten (die SUE-Funktion nutzt das letzte = jüngste Quartal). Gehört zur Plan-E-Daten-Integration.

### Aus Plan E (Review 2026-06-17 — Ports/Logik gebaut, echte Datenquellen folgen)

- [ ] **Echte Datenadapter für die neuen Stub-Ports anbinden** *(die zentrale „Go-Live"-Aufgabe)*.
  Plan E hat Ports + Agenten-Logik gebaut; die Agenten liefern korrekt `UNAVAILABLE`, bis echte Quellen angebunden sind:
  - **COT** (`COTProvider`): CFTC Commitments of Traders (wöchentlich, CSV) → `adapters/data/cftc_cot.py`.
  - **Commodity Supply** (`CommoditySupplyProvider`): EIA (Öl/Gas), USDA (Agrar), LME (Metalle) → Lagerbalancen + Produktionskosten-Kurve.
  - **Fear&Greed** (`SentimentDataProvider`): CNN Fear&Greed API → `adapters/data/cnn_fear_greed.py` (URL im `sentiment_stub.py` dokumentiert).
  - **Index-Daten** (`MarketDataProvider.get_index_constituents` / `get_constituent_histories` / `get_index_fundamentals` / `get_index_holdings`) — aktuell Default-Stubs (leer).
  **Ansatz:** je Quelle einen Adapter implementieren, der die jeweilige Port-Methode befüllt; die Agenten schalten dann automatisch von `UNAVAILABLE` auf echte Signale (keine Agenten-Änderung nötig).
  *(`get_real_rate_history` (FRED DFII10) ist erledigt — siehe gemergte Realzins-/Zins-Adapter.)*
- **Total-Return-Historie: bewusst NICHT umgesetzt** (2026-06-18). Für die Schweizer Sicht ist Price Return (steuerfreier Kapitalgewinn) der passende Default; TR unterstellt steuerfreie Dividenden-Reinvestition (idealisierte Brutto-Benchmark, ignoriert Steuern). Der tote Haken (`get_total_return_history` im Port + TR-Vorzugslogik im `index_price_agent`) wurde entfernt.
- [ ] `core/domain/events.py` (+ `adapters/cache/result_cache.py`, `adapters/data/fred_api.py`): `datetime.utcnow()` → `datetime.now(timezone.utc)` (DeprecationWarning unter Python 3.12). *(Minor, Aufräumen.)*
- [ ] I3-Test trennscharf machen (`tests/agents/stock_deep_dive/precious_metals/test_precious_metal_price_agent.py::test_negative_real_yield_correlation_when_inverse`): monoton gegenläufige Daten nutzen, sodass Level-Korr ≈ −1, Return-Korr ≈ 0 — damit eine Regression auf Level-Korrelation den Test bricht. *(Minor, Testqualität.)*

---

## 8. DESIGN-ENTSCHEIDUNGEN (Frontend — docs/frontend_notes.md)

- [ ] Weltkarte vs. Tabelle für Buffett-Indikator-Widget
- [ ] Drill-down: Einzelland-Zeitreihe (10 Jahre) im Buffett-Widget
- [ ] Big Mac Index: Halbjährliche Daten-Refresh-Strategie (manuelle Pflege vs. API)
- [ ] Mobile-first oder Desktop-first
- [ ] Framework-Wahl: React / Vue / Svelte (noch nicht entschieden)
- [ ] Echtzeit-Refresh: WebSocket oder Polling für Dashboard-Updates

---

## 9. SHORTS AUSBAUEN (Feature-Richtung, Stand 2026-06-18)

**Leitprinzip — zwei getrennte Tracks (nicht vermischen):**
- **Track A — Aggressiver Einzelaktien-Short** (Gewinn-Motiv): „diese Aktie ist schlecht → Gewinn bei Fall". Input = Einzelaktien-Tiefenanalyse. Heimat = **Stock Deep Dive / Judgment**.
- **Track B — Defensiver Hedge** (Schutz-Motiv): „mein Buch ist zu exponiert → absichern". Input = **Portfolio-Aggregat** (Netto-Long, Beta, Klumpen) + **Makro-Regime** (Cockpit). Instrument = breiter Index/ETF. Heimat = **Portfolio-Manager + Cockpit**.
- Beide haben andere Inputs/Logik/Instrumente/Risiken. **Block #3** ist der Punkt, der entscheidet, welcher Track gilt.

**Vereinbarte Reihenfolge:** #1 + #2 zuerst (als **Track A**, Einzelaktien), dann #3 (Regeln + Track-B-Hedge), dann #4 (Backtest).

**Architektur-Entscheidungen (festgehalten 2026-06-18):**
- **Geteilte Fakten + Short-Schicht:** Die bestehenden Deep-Dive-Sub-Agenten beschaffen die Fakten EINMAL; eine eigene Short-Schicht interpretiert sie short-spezifisch. EIN Analyselauf → ZWEI unabhängige Urteile (Long via `derive_recommendation`, Short via neuer `derive_short_assessment`). **Short ≠ invertiertes Long.**
- **A zuerst, B später (beide fest eingeplant):** A = reine Funktion `derive_short_assessment` + `ShortAssessment`-Modell + Feld auf `DeepDiveResult` (strukturiertes Urteil, kein LLM). B = `ShortThesisAgent` (LLM-Fließtext-These + XAI) obendrauf, sobald die Engine steht. **B sitzt AUF A.**
- **`derive_short_assessment` asset-class-dispatched** (wie `derive_recommendation` mit `asset_class`): Equity-Zweig zuerst voll, andere Klassen fallen vorerst auf „bearish + #2-Sizing" zurück → spätere Klassen sind Erweiterung, **kein Redesign.**
- **Borrow-Kosten:** v1 **Hard-to-borrow-Proxy-Flag** (aus Short-Float/Float/DTC), KEIN erfundener Gebühren-Wert. Echte Leihgebühr später als **optionales manuelles Eingabefeld.**

**Asset-Klassen-Roadmap (verbindlich):**
- **Equity — Bauabschnitt 1 (jetzt):** volle eigene Short-These (Bilanz/Distress/Earnings-Verfall/Bewertungs-Extrem) + #2.
- **Rohstoff-Short — späterer Block (fest eingeplant):** eigene Short-Spezifika: **Roll-Yield/Carry** (Contango/Backwardation), **Cost-Curve-Boden** (Mean-Reversion-Floor), **Angebotsschock-Squeeze**. Eigene Datenbedürfnisse (Futures-Kurve, Produktionskosten).
- **Anleihen-Short — späterer Block (fest eingeplant):** eigene Spezifika: **Carry** (Kupon zahlt der Shortende), **Duration**, **Credit-Asymmetrie**.
- **Index/ETF:** kein „dieser Index ist schlecht"-Short → das ist **Track B (Hedge)**, Block #3.

**Unter Überlegung (breiter als Shorts, separat zu entscheiden):** **Futures als NEUE Anlageklasse** in Long UND Short aufnehmen. Betrifft die ganze Deep-Dive-Struktur (nicht nur Shorts) — eigener Brainstorming-/Scope-Entscheid, bevor das angefasst wird.

**Kriterien-Katalog als Flag-Registry (Design-Entscheidung 2026-06-18):**
Der Equity-Short-Katalog wird als **Liste von Flag-Definitionen** modelliert — je `name`, `kategorie`, `benötigte Felder`, `schwelle`, `gewicht`. Die Short-Schicht prüft jedes Flag **defensiv**: fehlen die Felder (`None`), feuert es nicht (kein Crash). Verfügbare Flags → `short_score`; nicht-verfügbare = **dormant** (im Katalog dokumentiert), bis ein Adapter die Quelle liefert → dann automatisch aktiv, **ohne Logik-Änderung**. Der VOLLSTÄNDIGE Katalog (verfügbar + dormant) wird im Spec festgehalten.
- **Verfügbar (in `bottom_up`):** Bewertungs-Extrem (`valuation_range`+`fundamentals`: KGV, EV/EBITDA, P/Book, P/FCF, PEG, Shiller-CAPE), Distress/Bilanz (`quality`: altman_z, interest_coverage, debt_to_equity, net_debt_ebitda, current_ratio, fcf_margin), Profitabilität (`quality`: roe/roa/roic, Margen), Earnings-Verfall (`earnings_trend`: estimate_revision, beat_rate), schwacher Burggraben (`moat.total_score`), Insider-Verkäufe (`insider.net_direction`), Squeeze (`short_interest`: DTC/Float — als Risiko), Wachstums-Abschwächung (`fundamentals.revenue_cagr_3y`).
- **Dormant (Quelle später):** Momentum/Technik (Death-Cross, <200-Tage, Abstand 52W-Hoch), negativer Katalysator (Schuldenfälligkeit, Covenant, Guidance-Cut), Accounting-Red-Flags (Beneish M-Score, Accruals, DSO/Vorräte), relative Schwäche (vs. Sektor), Verwässerung/Cash-Burn (Aktienzahl↑, Runway), Sentiment/Positionierung (überfüllter Long, Downgrades).

**Momentum = gemeinsam Long + Short (committet, eigener Folge-Block):** Sobald Momentum/Trend für Equity gebaut wird, kommt es als **neuer Bottom-up-Sub-Agent** (`MomentumSnapshot`, analog zum Index-Momentum-Agenten), der **BEIDE** Seiten speist — Long-Empfehlung (`derive_recommendation`-Alignment) **und** Short-Schicht (aktiviert die dormanten Momentum-Flags). Begründung (User): nutzt Short Momentum, muss Long es auch. In Block 1 bleibt Momentum dormant.

**Aktions-Taxonomie (long + short) — Erweiterung (festgehalten 2026-06-18, betrifft AUCH die Long-Seite):**
Jede Analyse gibt pro Linse genau eine Aktion. **HOLD vs NONE:** HOLD = Position existiert, Lage unklar → halten; **NONE = nicht investiert + kein belastbares Urteil**. Neu außerdem **Aufstocken (+)**: hält man bereits und das Einstiegssignal gilt weiter/verstärkt sich → nicht HOLD, sondern nachlegen.

| Lage | Long-Linse | Short-Linse |
|---|---|---|
| nicht gehalten + klares Einstiegssignal | **BUY** | **SHORT** |
| nicht gehalten + kein belastbares Urteil (neutral / bearish-aber-kein-Short / unklar) | **NONE** | **NONE** |
| gehalten + Einstiegssignal gilt weiter/verstärkt | **BUY+** | **SHORT+** (selten sinnvoll) |
| gehalten + Lage unklar | **HOLD** | **HOLD** |
| gehalten + These gekippt | **SELL** | **COVER** |

- **Short+ stark gegated:** Nachlegen in Shorts ist gefährlich (Risiko wächst überproportional, Squeeze) → nur wenn These *verstärkt* UND Position nicht im Verlust/Squeeze; **nie** in einen gegen dich laufenden Short nachlegen. Default konservativ/aus.
- **„Verstärkt" vs „gilt weiter":** v1 = gehalten + weiterhin starkes Einstiegssignal → „+"; echtes „verstärkt" (Vergleich zur letzten Analyse) nutzt die Memory-Historie später.
- **Betrifft die Long-Seite:** `derive_recommendation` + `Recommendation`-Enum bekommen **NONE + BUY+** und die HOLD-vs-NONE-Unterscheidung. Braucht den Positions-Input **`current_position` (none/long/short)** statt des bool `in_portfolio`.
- **Eigener Foundation-Block:** weil es die Long-Seite berührt (Regressionsrisiko) → als fokussierter „Aktions-Taxonomie"-Block **vor** der Short-Engine umsetzen; die Short-Engine nutzt ihn dann.

### Block #1 — Short-Kandidaten finden („das Was")
- **Ziel:** Eine **eigene Short-These** statt des heutigen „bearish → SHORT"-Kippschalters. Bewertet gezielt **Short-Würdigkeit** mit short-spezifischen Kriterien — NICHT das Spiegelbild der Kauf-Kriterien.
- **Kriterien (Beispiele):** extreme Überbewertung, **fallende/negative Gewinne** + negative Earnings-Revisions, **negatives Momentum/Death-Cross**, **Bilanz-/Quality-Warnsignale** (hoher Leverage, niedriger Altman-Z, schwacher Piotroski, negativer FCF), ggf. hoher Short-Interest als Bestätigung *und* Squeeze-Warnung.
- **Umfang (pragmatisch):** (1) **on-demand Short-Urteil pro Ticker** (nutzt den bestehenden Deep-Dive-Fluss) + (2) optional **begrenzter Screen** über ein handhabbares Universum (Index-Konstituenten oder die eigenen Portfolio-Longs). **Kein** Voll-Markt-Screener, **keine** Watchlist-Infrastruktur (vorerst).
- **Output:** Short-Score + begründete These je Titel.
- **Heute vorhanden:** nur `derive_recommendation` (bearish → SHORT) + `short_interest_agent`. Es fehlt die eigene Short-These-Logik.

### Block #2 — Short-Risiko & Positionsgröße („das Wie viel")
- **Ziel:** Das Spezifische am Shorten sauber modellieren — setzt **nach** einer vorhandenen Idee an (findet keine Ideen).
- **Inhalte:** **Borrow-Kosten** (Leihgebühr p. a.), **Squeeze-Risiko** (days-to-cover/Short-Float → Warnung + Deckelung), **asymmetrisches Verlustprofil** (Verlust nach oben theoretisch unbegrenzt → konservativere Größe), **Positionsgröße + Stop-Logik** (vol-/konfidenz-skaliert).
- **Output:** empfohlene Positionsgröße (% NAV), Stop, Squeeze-/Borrow-Flags.
- **Heute vorhanden (Plan A):** `derive_recommendation` hat bereits `_position_size_pct`, `days_to_cover`/`short_float_pct`-Parameter + Squeeze-Warnung ab DTC≥5 — als Basis ausbaubar.

### Block #3 — Anlagephilosophie / Regeln („das Ob")
- **Ziel:** Übergeordnete Leitplanke + **die Track-Weiche**: *darf* man gerade short, und in welcher Form?
- **Inhalte:** defensiver Hedge (Index/ETF) vs. aggressiv (Einzeltitel); **regime-abhängig** (aggressive Shorts nur in bearishen Makro-Phasen); Cash-vs-Short; **Track B konkret**: regime-getriebene Hedge-Vorschläge im **Portfolio-Manager**, dimensioniert auf das **Netto-Long-Exposure** des Portfolios.
- **Heute vorhanden:** `_short_type` (defensiv/aggressiv) + SHORT_WARNINGS; Portfolio-Manager überwacht Cash/Klumpen — aber keine regime-getriebene Hedge-Logik.

**Portfolio-Manager-Ausbau (Befund 2026-06-18, gehört zu Track B / Block #3):**
- **Heute long-only:** `data/portfolio.json`-Positionen haben **kein Richtungs-Feld** (`ticker, shares, buy_price, currency, sector, asset_class, country`). `portfolio_monitor_agent` rechnet P&L (`(current-buy)/buy`), Klumpen- und Exposure-Logik **als wäre alles long** — er **erkennt nicht**, ob eine Position long oder short ist.
- **Nötig:** (1) `direction`/`side`-Feld („long"|"short") je Position; (2) short-bewusste P&L (invertiert) + Netto-Long-vs-Short-Exposure; (3) daraus die **„aktuelle Position" (none/long/short)** ableiten, die die Short-Aktions-Logik (SHORT/COVER/HOLD) speist.
- **Heute** geht an die Urteilslogik nur ein **bool `in_portfolio`** (CLI-Flag), nicht die echte Position. Block 1 nimmt die Position als **einfachen Parameter** entgegen; das **automatische Ableiten aus dem echten Depot inkl. Richtung** ist PM-Ausbau (hier).
- **Interplay (später):** Bist du short und das Signal dreht bullish → Short-Linse sagt COVER, Long-Linse sagt BUY → die **Reconciliation** (was tun, wenn beide Linsen feuern) gehört in den PM.
- **Aktions-Symmetrie (festgehalten):** Long = BUY/SELL/HOLD, Short = SHORT/COVER/HOLD; je „Einsteigen/Aussteigen/Nichts ändern", HOLD ist der Auffangkorb (auch bei Unklarheit), **kein „NONE"**.

### Block #4 — Shorts im Backtest / Bewertung („Hat's funktioniert")
- **Ziel:** Ehrlich messen, ob alte Short-Calls **wirklich** Geld gebracht hätten — getrennt von Long-Calls.
- **Inhalte:** **gespiegelte Returns** (Short verdient bei Fall), **Borrow-Kosten** im Backtest, **asymmetrisches Risiko**/MaxDrawdown der Short-Seite, Hit-Rate **vs. Payoff** (eine hohe Trefferquote kann durch seltene Squeeze-Großverluste negativ werden).
- **Heute vorhanden (Plan A):** Backtester spiegelt SHORT/SELL-Returns bereits vorzeichen-korrekt; Borrow-Kosten + getrennte Short-Auswertung fehlen.

### Geklärte Design-Fragen (Stand 2026-06-18)
- **Screener:** NICHT in Block 1. Bauabschnitt 1 = on-demand Short-Urteil pro Equity-Analyse (kein Screener, keine Watchlist). Screener = eigene spätere Sache.
- **Borrow-Kosten:** Proxy-Flag (v1) + optionales manuelles Feld (später).
- **Regime-Gate:** Das Regime-Veto ist Teil der Short-Schicht (Cockpit fließt in `derive_short_assessment` ein); die volle Regeln-/Track-Weiche ist Block #3.

### Build-Status & offene Blöcke (im Code geprüft 2026-06-19)

**✅ Erledigt:** Foundation-Block (PR #3) · Block 1 + 1b (`core/domain/short_assessment.py` `derive_short_assessment`, im `judgment_agent` verdrahtet, `detect_conflict` bidirektional) · `AnomalyReport.direction` als Block-1-Voraussetzung (`core/domain/models.py`) · Feld-Set von `ShortAssessment` steht.

**⏳ Offen (verifiziert noch nicht im Code):**
- [ ] **Konflikt-Agent (Folge-Block, short.md §18)** — eigene LLM-Reversal-Abwägung bei `conflict` (Block 1 *erkennt* nur). **In Umsetzung auf Branch `feat/conflict-agent`** (Spec + Plan + erste Commits, 4-Task-Plan) — finaler Status beim End-Abgleich der Short-Blöcke prüfen.
  Spec: `docs/superpowers/specs/2026-06-19-konflikt-agent-design.md` · Plan: `docs/superpowers/plans/2026-06-19-konflikt-agent.md`.
  **Umfang laut Spec:** **beratend** (ändert keine formale Aktion); `ConflictResolution`-Modell (Verdikt `EXIT`/`HOLD`/`REVERSE` + Reasoning, vom LLM via `VERDICT:`-Zeile, Parse-Fehler → `HOLD`) an `DeepDiveResult`; `ConflictAgent` (`agents/conflict/`, LLM wie `JudgmentAgent`); **bedingter Call** im `judgment_orchestrator` (kein Chief); Anzeige in `app/main.py`; Persistenz via `memory.save_analysis` + Konsum von `backtester_context`. **Verdikt-Auswertung gegen Forward-Returns + Kalibrierung = Block #4.**
- [ ] **Block #3 — Regeln/Regime-Weiche + Track-B-Hedge + Portfolio-Manager-Ausbau.** `portfolio_monitor_agent` hat **kein** `side`/`direction`-Feld (heute long-only).
  **Ansatz:** `side` (long/short) je Position in `portfolio.json`; short-bewusste P&L (invertiert) + Netto-Exposure; daraus `current_position` (none/long/short) ableiten; Reconciliation (beide Linsen feuern).
  - **3a in Review (PR #7, 2026-06-20):** `Position`-Modell + `PortfolioPort` + `JsonPortfolioProvider` + richtungs-bewusster Monitor (P&L/Exposure/Klumpen netto) + `current_position` aus dem Depot, CLI-`--position` entfernt. **Review-Befunde im Branch gefixt** (TDD, Gesamtsuite 709 grün): **F1** Alignment-Warnung jetzt richtungs-bewusst (short fehlausgerichtet bei COVER/BUY statt SELL/SHORT — Short+SHORT ist Ausrichtung, kein Fehlalarm mehr); **F2** englische Monitor-Kommentare auf Deutsch (AGENTS.md §0); **F3** `shares`/`buy_price` werfen wie `direction` `PortfolioError` (fail-loud konsistent); **F4** Monitor druckt Netto **und** Brutto getrennt. **PR #7 am 2026-06-20 gemergt** (Merge-Commit `dfda4b7`) — Review-Änderungen F1–F4 wie oben, Gesamtsuite 709 grün.
  - **F1-Nachbesserung (Nach-Merge-Review PR #7, 2026-06-20):** Die in PR #7 gefixte Short-Alignment-Warnung war *logisch* korrekt, **feuerte aber in Produktion nie** (Persistenzlücke): `save_analysis` persistierte nur die **Long**-Aktion unter `recommendation`; die Long-Linse deferiert bei Short-Positionen auf `NONE` → `COVER` landete nie in der History, der Short-Zweig matchte nie. Zudem waren `SHORT` (Long-Zweig) und `BUY` (Short-Zweig) vestigial (werden nie ausgegeben; `ShortAction` kennt kein BUY). **Fix (eigener PR, TDD, Gesamtsuite 711 grün):** (1) **`short_action` als eigene DB-Spalte** in `analysis_memory` persistiert (`result.short_action.value`, symmetrisch zu `recommendation`); (2) Monitor liest für Shorts `short_action` (feuert bei `COVER`), für Longs `recommendation` (feuert bei `SELL`); (3) vestigiale `SHORT`/`BUY` entfernt. **⚠️ Deploy-Schritt:** vor Merge/Deploy einmalig auf Supabase `ALTER TABLE analysis_memory ADD COLUMN short_action text;` ausführen, sonst schlägt jeder `save_analysis`-INSERT fehl. **PR #9 am 2026-06-20 gemergt** (Merge-Commit `7e6e2f2`) — Migration vorab ausgeführt (Spalte `short_action` in der DB verifiziert), Gesamtsuite 711 grün.
  - [ ] **Risiko-Kennzahlen verfeinern: Beta-/Korrelations-bereinigtes Netto-Exposure + ETF-Look-Through** *(Befund 2026-06-20 aus PR#7-Review, fachliche Folge von 3a — User-Einwand).*

    **Problem.** Das in 3a eingeführte `net_exposure = Σ long − Σ short` verrechnet **jeden** Long-Dollar mit **jedem** Short-Dollar — **unabhängig davon, ob die beiden Positionen überhaupt korreliert sind**. Diese Verrechnung ist nur korrekt für eine *gleichförmige* Marktbewegung (alle Titel steigen/fallen im Gleichschritt). In der Realität entstehen zwei irreführende Fälle:
    - **Unkorreliertes Paar (z. B. Nestlé long / Öl short):** `net = 0` suggeriert „marktneutral", obwohl es zwei **unabhängige, ungedeckte** Wetten sind (Basiskonsum vs. Energie sind kaum korreliert). *Heute teilweise abgefangen:* die Klumpen-Prüfung rechnet **pro Bucket** (Sektor/Anlageklasse/Land) gegen, daher landen Nestlé und Öl in **verschiedenen** Sektor-Buckets und feuern je einen Klumpen-Alarm — der Monitor tut also nicht so, als wäre alles sicher. Die **Netto-Skalarzahl allein** kann die beiden Fälle aber nicht unterscheiden.
    - **ETF long / Einzelaktie short (z. B. SPY long / Tesla short):** doppelt heikel und vom Klumpen-Netz **schlechter** abgedeckt:
      (a) **Beta-Mismatch + Idiosynkrasie:** Ein breiter ETF hat Markt-Beta ≈ 1, eine Einzelaktie ein abweichendes Beta (Tesla ≈ 1,8) **plus** firmenspezifisches Risiko, das im Korb nicht vorkommt. Beta-bereinigt ist man real eher **netto short** den Markt (`100·1 − 100·1,8 = −80`), nicht neutral — die naive 0 verschleiert sowohl die Markt-Wette als auch die konzentrierte Einzeltitel-Wette.
      (b) **ETF passt in keinen einzelnen Bucket:** ein ETF ist ein Korb über viele Sektoren/Länder, das `Position`-Modell gibt einer Position aber nur **ein** `sector`/`asset_class`/`country`-Feld → die Klumpen-Prüfung kann den ETF nicht sinnvoll bucketen und bleibt evtl. **still** (z. B. `etf` vs. `equity` je 50 % < 60 %-Asset-Klassen-Schwelle → kein Alarm). *(Mini-Teilabsicherung: ist der geshortete Titel Bestandteil des ETFs, hebt der Short nur dessen kleinen Anteil im Korb auf; der Rest bleibt voll long.)*

    **Wurzel.** Eine einzelne Netto-Skalarzahl kann „echte Absicherung" nicht von „zwei getrennten Wetten" unterscheiden, weil ihr **Beta/Korrelation** fehlt — und bei ETFs zusätzlich die **Durchschau** auf die Bestandteile.

    **Ansatz (zwei Stufen, je eigene Datenquelle):**
    1. **Beta-/Korrelations-bereinigtes Netto-Exposure.** Je Position ein Markt-Beta beschaffen (Quelle: yfinance `info["beta"]` oder selbst per Regression der Positionsrenditen gegen den Heimat-Index aus der Kurshistorie) und zusätzlich zum naiven Netto ein `net_beta = Σ (signed_value · beta) / NAV` im Snapshot ausweisen (analog zu `long_value`/`short_value`/`net_exposure`). Ausbaustufe: echte **Kovarianz-/Korrelationsmatrix** statt Einzel-Beta. Anknüpfpunkt im Code: die `returns_provider`-basierte Portfolio-Vola in `_evaluate_positions` erfasst Korrelation **bereits korrekt**, sobald echte Kursreihen anliegen — sie ist heute schon die ehrlichste Risikozahl, nur noch nicht produktiv verdrahtet.
    2. **ETF-Look-Through (Durchschau).** Einen ETF nicht als eine Sektor-/Länder-Position behandeln, sondern über eine Holdings-Quelle (`MarketDataProvider.get_index_holdings`, siehe §5/Plan E „Index-Daten") in seine **Bestandteils-Gewichte** aufschlüsseln und diese in die Klumpen-/Exposure-Buckets einrechnen. Nebeneffekt: ein Short auf einen ETF-Bestandteil hebt automatisch nur dessen Anteil im ETF auf, nicht die ganze Position.

    **Abhängigkeiten:** (1) Beta-/Kursdaten pro Position; (2) ETF-Holdings-Quelle (überschneidet sich mit §5/Plan E). **Prio: mittel** — **kein Rechenfehler** im Bestehenden, aber `net_exposure` ist als *alleinige* Hedge-Aussage irreführend. Bis dahin liefern die **Klumpen-Alarme** und (bei verdrahtetem `returns_provider`) die **Portfolio-Vola** die ehrlichere Risikosicht.
- [ ] **Block #4 — Short-Backtest** — gespiegelte Returns, Borrow-Kosten, getrennte Short-Auswertung + Kalibrierung des Konflikt-Agenten. *(Backtester spiegelt SHORT/SELL bereits vorzeichen-korrekt; Borrow-Kosten + getrennte Auswertung fehlen.)*
- [ ] **Track B — `ShortThesisAgent` (LLM)** — Fließtext-These + XAI auf der Engine.
- [ ] **Equity-Momentum-Agent (long + short)** — `MomentumSnapshot` (analog Index), aktiviert die dormanten Momentum-Flags. *(Equity hat noch keinen Momentum-Agenten.)*
- [ ] **Asset-Klassen-Shorts** — Rohstoff (Roll-Yield/Carry, Cost-Curve-Boden), Anleihe (Carry/Duration/Credit-Asymmetrie), Edelmetall. Je eigener Block.
- [ ] **Futures als neue Anlageklasse** (long + short) — eigener Scope-/Brainstorming-Entscheid **vor** Umsetzung.
- [ ] **Borrow-Rate manuell** — optionales Eingabefeld als Ergänzung zum Hard-to-borrow-Proxy-Flag.

---

## 10. FINANZ-KONZEPT-REVIEW 2026-06-16 — STATUS (im Code geprüft 2026-06-19)

Die CFA-Review `docs/finanz_konzept_review_2026-06-16.md` (~50 Befunde: ❌ falsch · ⚠️ verbesserungswürdig) wurde am 2026-06-19 gegen den aktuellen Code abgeglichen.
**Ergebnis: weitgehend umgesetzt** (Pläne A–E, 06-16 bis 06-18). **Alle ❌-Befunde** und die strukturellen Prio-1–3-Punkte aus Teil B sind erledigt. Offen sind nur Daten-Anbindungen (Stubs) und einzelne Verdrahtungen — bereits in §1–§7 erfasst. **Kein Einzel-Import der erledigten Befunde**, um keine Schein-Todos anzulegen.

### ✅ Erledigt — Beleg im Code (NICHT erneut eintragen)
- **Backtest-Validität (1.1):** fixe `HORIZONS_DAYS`, `forward_return`, `hit_rate_ci`, Benchmark-Bereinigung, delistet-Handling; `top_down_backtester` = echter Prognose-Backtest (Regime t → Benchmark t+h).
- **Risikokennzahlen (1.2):** `core/utils/performance_metrics.py` (sharpe/sortino/max_drawdown/profit_factor); `_position_size_pct` in `recommendation.py`.
- **Stubs ≠ NEUTRAL (1.4):** `aggregation.weighted_signal` ignoriert UNAVAILABLE + re-normalisiert die Gewichte.
- **DCF (2.1):** echtes `two_stage_dcf` + `capm_wacc`.
- **Edelmetall-Bewertung (2.2):** `real_rate_anchor` preis-unabhängig, `weighted_median_range` statt Min/Max-Union.
- **Credit-Rating (2.3):** kein `startswith`-Skalen-Mismatch mehr.
- **Niveau→Momentum (2.4):** `energy`/`industrial_metals` via Z-Score; Metalle als **Copper/Gold-Ratio**.
- **CAPE/ERP (2.5):** CAPE aus `fundamentals` entfernt; `index_valuation` mit `earnings_yield`/`equity_risk_premium`/`shiller_cape`.
- **Relativ/real/Sub-Signale (3.1–3.3):** reales Kreditwachstum (`to_real`), Money-Supply `excess_over_nominal_gdp` (lückenlose Bänder), `macro_chief.detect(sub_signals=…)`; **alle** Chiefs aggregieren via `weighted_signal` (macro/sentiment/yield_curve/equity/index).
- **VIX contrarian (3.4)** · **Insider wertgewichtet + Sektor benchmark-relativ (3.6)** · **`_RATE_HISTORY` → `DatedHistoryPort` (3.7)**.
- **Statistik (4.1):** `robust_z_score` (MAD/Iglewicz-Hoaglin) + `bonferroni_z_threshold`.
- **Wilder-RSI + MA200 ≥ 2y (4.2)** · **echtes Commodity-Perzentil (4.3)** · **lückenlose Bänder Inflation/Geldmenge (4.4)** · **Portfolio FX/HHI/Max-DD**.

### ⏳ Noch offen — bereits anderswo erfasst (kein Duplikat anlegen)
- **Konfidenz-Kalibrierung (1.3)** → §4 `recommendation.py` (Buckets leer, Fallback 0.70).
- **Daten-Stubs** (COT, Supply/Demand, Fear&Greed, Bond-Rohdaten, Index-Konstituenten) → §2/§3/§5 + Plan E.
- **Verdrahtungen** (Money-Supply-Velocity-Trend, Yield-Curve-Bull-Steepening `prev_10y3m`, Interest-Rate-Richtung-History, EU/CH-Sahm-Historie) → §D1. *(Logik je vorhanden, `run()` übergibt noch `None`.)*
- **Bond-Detail** (Yield-to-Worst, Convexity in Preisänderung, OAS-Effective-Duration, Recovery/LGD/Credit-Triangle) → §2 (Bond-Daten) + §7 (Plan C).
- **Total Return vs. Price Return (4.6)** → §7/Plan E: für CH bewusst Price Return als Default (nicht umgesetzt).

### ⏳ Neu erfasst (war noch nirgends notiert)
- [ ] **`agents/stock_deep_dive/precious_metals_chief_agent.py` (Z. 45/56): `cot_signal=Signal.NEUTRAL` hart verdrahtet** trotz vorhandenem `cot_agent`.
  **Ansatz:** sobald COT-Daten angebunden sind (§3), `cot_agent`-Signal einspeisen statt fix NEUTRAL.
- [ ] **`commodity_chief`/`precious_metals_chief`: gewichtete Signal-Synthese + `currency_impact` (USD-Effekt) prüfen/ergänzen** (Review Domäne 7: nur Einsammeln ohne Zuverlässigkeits-Gewichtung; Saisonalität mit n<10 nicht heruntergewichtet).
  **Ansatz:** `weighted_signal` analog den übrigen Chiefs; Saisonalität klein gewichten; USD-Effekt erfassen.
