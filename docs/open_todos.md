# Open TODOs

Alle offenen Aufgaben aus Codebase, Code Review (2026-06-05) und Plan-Dateien.
Stand: 2026-06-16 | Nach Erledigung: Zeile abhaken oder entfernen.

---

## GESAMTÜBERSICHT

| Bereich | Offen |
|---------|-------|
| Offene Bugs (code_review_2026-06-05.md) | 12 |
| Stub-APIs (ECB, SNB, etc.) | 20+ Methoden |
| Agent-Stubs (komplette Implementierung fehlt) | 5 Agents |
| Fehlende Einzelfeatures in bestehenden Agents | 15 |
| Feature-Backlog (Pläne) | ~36 Tasks |
| Test-Lücken | 6 |
| Code-Qualität / toter Code | 3 |
| Design-Entscheidungen (Frontend) | 10 |

---

## 1. OFFENE BUGS (aus code_review_2026-06-05.md)

### Kritisch (Crash / Datenverlust)

- [ ] **Bug #1** — `adapters/cache/result_cache.py:233`
  `BottomUpResult` braucht 13 Felder; `load_bottom_up()` übergibt nur 11 — `index` und `commodity_deep` fehlen.
  Raises `TypeError` jedes Mal wenn eine frische Bottom-Up-Cache-Datei existiert (normaler Happy Path).
  **Lösung:** Die zwei fehlenden Felder analog zu den anderen 11 aus JSON lesen und übergeben.

- [ ] **Bug #2** — `app/main.py:130`
  `JudgmentOrchestrator(llm, bus)` — fehlt `memory` als drittes Argument.
  Crasht sofort im `judge`-Modus. Das `memory`-Objekt ist weiter oben bereits instanziert.

- [ ] **Bug #4** — `adapters/memory/supabase_memory.py:128-129`
  Anomalie-Schweregrade sind hartcodiert auf `"none"` — die echten `AnomalyReport.severity`-Werte werden nie in die DB geschrieben.
  Jede Datenbankzeile ist permanent korrumpiert.
  **Lösung:** `result.top_down_anomaly.severity if result.top_down_anomaly else "none"` (analog bottom_up).

- [ ] **Bug #5** — `adapters/memory/supabase_memory.py`
  `psycopg2.connect()` wird in jeder Methode geöffnet, nie geschlossen → Connection Pool Leak.
  **Lösung:** `_connect()` als `@contextmanager` mit `conn.close()` in `finally`-Block.

### Medium Severity

- [ ] **Bug #26** — `agents/market_cockpit/macro/shiller_cape_agent.py:29`
  Kein unterer Schwellenwert für BULLISH — jeder CAPE-Wert unterhalb des Durchschnitts, egal wie weit, erzeugt BULLISH.
  Ein Markt im Kollaps erzeugt dasselbe Signal wie einer, der leicht unterbewertet ist.

- [ ] **Bug #30** — `agents/market_cockpit/macro_chief_agent.py:82`
  `EXPANSION` als Default-Regime wenn alle Provider ausfallen.
  Nachgelagerte Agenten generieren aktionabel wirkende "buy Tech" Empfehlungen ohne reale Datenbasis.
  **Lösung:** Default auf `NEUTRAL` oder `UNKNOWN` setzen.

- [ ] **Bug #34** — `agents/stock_deep_dive/bond/bond_metrics_agent.py:47`
  `if ytm and inflation` schlägt für Zero-Coupon-Anleihen (`ytm=0.0`) fehl.
  Real-Yield wird `None` statt `-inflation`, versteckt genuinen negativen Real-Yield.
  **Lösung:** `if ytm is not None and inflation is not None`.

- [ ] **Bug #36** — `agents/stock_deep_dive/commodity/supply_demand_agent.py:77`
  `_signal()` ist definiert aber wird nie aufgerufen. `signal=Signal.NEUTRAL` ist hartcodiert.
  Gesamte Signallogik ist toter Code.

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
- [ ] Shiller CAPE (`shiller_cape=None`) — Quelle: Quandl / multpl.com

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

---

## 8. DESIGN-ENTSCHEIDUNGEN (Frontend — docs/frontend_notes.md)

- [ ] Weltkarte vs. Tabelle für Buffett-Indikator-Widget
- [ ] Drill-down: Einzelland-Zeitreihe (10 Jahre) im Buffett-Widget
- [ ] Big Mac Index: Halbjährliche Daten-Refresh-Strategie (manuelle Pflege vs. API)
- [ ] Mobile-first oder Desktop-first
- [ ] Framework-Wahl: React / Vue / Svelte (noch nicht entschieden)
- [ ] Echtzeit-Refresh: WebSocket oder Polling für Dashboard-Updates
