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

### Noch offen (für Bauabschnitt-1-Design)
- Genaues Feld-Set von `ShortAssessment` (Score, Thesen-Flags, Risiko-Block) + konkrete Equity-Kriterien/Schwellen.
