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
>
> **PR-Protokoll (§5):** Audit + die zwei Folge-Test-Lücken aus #1/#2 → **PR #12 am 2026-06-20 gemergt** (Merge-Commit `eb044a0`). Review (gemeinsam): alle 7 Code-Belege gegen `master` verifiziert, zitierte Tests grün. *(Dieser Protokoll-Vermerk selbst: bewusste Direkt-auf-`master`-Ausnahme — er braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*

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

- [x] **Bug #30** — `agents/market_cockpit/macro_chief_agent.py:82`
  `EXPANSION` als Default-Regime wenn alle Provider ausfallen.
  Nachgelagerte Agenten generieren aktionabel wirkende "buy Tech" Empfehlungen ohne reale Datenbasis.
  **Lösung:** Default auf `NEUTRAL` oder `UNKNOWN` setzen.
  **✅ Audit 2026-06-20 → behoben (TDD).** Befund: Der gefährliche Laufpfad (`run()` bei Provider-Ausfall) war schon entschärft; offen war nur der statische `MacroChiefAgent.default()` (regime `EXPANSION`, confidence `0.5`), genutzt als Fallback in `top_down_orchestrator.py:44`. **Wichtig:** Enum `MarketRegime` hat **kein** `NEUTRAL`/`UNKNOWN` → die Logbuch-Lösung war nicht 1:1 möglich. **Umgesetzt:** `default()` → `MarketRegime.SLOWDOWN` (neutralstes vorhandenes, defensives Regime, konsistent zum `run()`-Pfad bei leerem State) + `regime_confidence=0.2` (signalisiert „keine Datenbasis"). Fachlich: ein falsch-positives Risk-on ist asymmetrisch teurer als ein zu vorsichtiges Regime. Festnagelnder Test (`test_macro_chief_default`) auf SLOWDOWN + niedrige Confidence angepasst; die übrigen `EXPANSION`-Stellen in Tests sind Beispiel-Eingaben (unberührt). Gesamtsuite **737 grün**.
  **PR-Protokoll (§5): PR #17 am 2026-06-21 gemergt** (Merge-Commit `18f35db`). Review (gemeinsam): Diff statisch gegen `master` verifiziert — Regime-Detektor (SLOWDOWN gewinnt bei `composite=0.0`), Orchestrator-Fallback (`top_down_orchestrator.py:44`), Downstream-Konsumenten; die Default-Confidence `0.2 < 0.4` greift korrekt in `recommendation.py:105` (−0.10). Gesamtsuite **737 grün** unabhängig im isolierten Worktree bestätigt. Branch `fix/bug30-macro-default-regime` gelöscht. *(Dieser Vermerk: bewusste Direkt-auf-`master`-Ausnahme — er braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*

- [x] **Bug #34** — `agents/stock_deep_dive/bond/bond_metrics_agent.py:47`
  `if ytm and inflation` schlägt für Zero-Coupon-Anleihen (`ytm=0.0`) fehl.
  Real-Yield wird `None` statt `-inflation`, versteckt genuinen negativen Real-Yield.
  **Lösung:** `if ytm is not None and inflation is not None`.
  **✅ Audit 2026-06-20 BEHOBEN:** `bond_metrics_agent.py:90` nutzt `if ytw is not None and infl is not None` (Real-Yield aus YTW); `crate is not None` lässt Zero-Coupon korrekt durch — `0.0` wird nicht mehr fälschlich als `None` behandelt.

- [x] **Bug #36** — `agents/stock_deep_dive/commodity/supply_demand_agent.py:77`
  `_signal()` ist definiert aber wird nie aufgerufen. `signal=Signal.NEUTRAL` ist hartcodiert.
  Gesamte Signallogik ist toter Code.
  **✅ Audit 2026-06-20 BEHOBEN:** `supply_demand_agent.py:75` ruft `signal=_signal(pct)` im AVAILABLE-Zweig real auf; hartes NEUTRAL nur noch im legitimen `_DEFAULT`/UNAVAILABLE-Pfad (kein Provider/keine Daten). Tests (`test_low/high/normal_inventory`, `test_run_available_with_inventory`) beweisen echtes BULLISH.

- [x] **Bug #42** — `agents/stock_deep_dive/index/index_price_agent.py:61-62`
  `close.index.searchsorted(f"{datetime.utcnow().year}-01-01")` wirft `TypeError` bei timezone-aware Index.
  Ausserdem: wenn Jahresanfang nicht im 5-Jahres-Fenster liegt, wird YTD falsch berechnet.
  **✅ Audit 2026-06-20 → behoben (TDD).** Teil 1 (tz-aware-Crash) war bereits gefixt (`datetime.now(timezone.utc)` + String-`searchsorted`, durch `test_ytd_uses_timezone_aware_now` abgesichert). **Offener Rest (dieser PR):** liegt der 1.1. **vor** dem ersten Datenpunkt (Index erst seit z. B. März gelistet), liefert `searchsorted` `0` und `iloc[0]` (ein Mid-Year-Kurs) wurde fälschlich als Jahresanfangs-Basis genommen → verzerrte YTD. **Lösung:** Guard `if 0 < ytd_idx < len(close)` — bei `ytd_idx == 0` (kein Datenpunkt vor dem 1.1.) ist YTD jetzt `None` statt einer Scheinzahl; oberer Rand (`>= len`) wie zuvor None. 2 neue Tests (März-Start → None; über-Jahreswechsel → gesetzt), Jahr dynamisch (zeitstabil). Gesamtsuite **739 grün**. *(PR: `fix/bug42-index-ytd-window`.)* **PR #16 am 2026-06-21 gemergt** (Merge-Commit `c5ae98e`). Im Review noch 3 Punkte ergänzt (kein Verhalten geändert): YTD-Basis-Konvention im Code-Kommentar erläutert **und** als Folge-Aufgabe §4 protokolliert (erster Handelstag des Jahres vs. gebräuchlicherer Vorjahres-Schlusskurs), Edge-Case „1.1. == erster Datenpunkt" (Börsenfeiertag) vermerkt, `datetime`-Import an den Test-Modulkopf gezogen.

- [x] **Bug #44** — `agents/stock_deep_dive/equity/fundamentals_agent.py`, `insider_agent.py`, `short_interest_agent.py`
  Keine Exception-Guard auf Provider-Response (kein `if isinstance(data, Exception)`).
  Inkonsistent mit `quality_agent.py` (hat den Guard). Exceptions propagieren unkontrolliert.
  **✅ Audit 2026-06-20 → behoben (TDD).** Befund: `fundamentals_agent` hatte den Guard bereits (robuster als `quality_agent`: `try/except` **plus** `isinstance`). Offen waren `insider_agent` + `short_interest_agent`. **Lösung:** dasselbe robuste Muster (`try/except Exception` → leere Liste/Dict, **plus** `isinstance(..., Exception)`-Guard) in beide `run()` ergänzt → Rückfall auf neutralen Default statt Crash. Deckt beide Fehlermodi ab (Provider **wirft** und Provider **gibt Exception zurück**). Je 2 neue Tests; Gesamtsuite **715 grün**. **PR #13 am 2026-06-20 gemergt** (Branch `fix/bug44-equity-exception-guards`; im Review noch Snapshot-Imports an den Dateikopf gezogen — reine Stil-Kosmetik, kein Verhalten geändert).

- [x] **Bug #46** — `adapters/memory/supabase_memory.py:44`
  Breites `except AttributeError: pass` schluckt alle Fehler still.
  Jede Umbenennung von `CockpitResult`-Unterfeldern führt zu einem leeren Snapshot ohne Fehlermeldung.
  **✅ Audit 2026-06-20 → behoben (TDD).** Befund: das stille `except AttributeError: pass` lag **3×** in der Datei (`_build_indicators_snapshot` + 2× in `save_analysis`: Bottom-Up-Indikatoren + Regime). **Lösung:** modul-lokaler Defensiv-Helfer `_safe_value(getter, what=…)` (loggt via `logging.warning(..., exc_info=True)` statt still zu schlucken, liefert `_MISSING`-Sentinel) + `_put(snap, key, getter, allow_none=…)`. Alle 3 Stellen lesen jetzt **granular**: ein umbenanntes Feld überspringt nur sich selbst (+ Log), reißt die folgenden Indikatoren nicht mehr mit. 4 neue Tests (Granularität + Logging für alle 3 Stellen); Gesamtsuite **719 grün**. **Bewusst klein gehalten** — der projektweite zentrale `_safe`-Helfer für Provider-Calls bleibt das separate Feature aus §7 (PR #14). *(PR: `fix/bug46-supabase-silent-except`.)*

- [ ] **Bug #47** — `agents/stock_deep_dive/equity_chief_agent.py`, `bond_chief_agent.py`, `commodity_chief_agent_mikro.py`
  Chief Agents sammeln Sub-Agent-Ergebnisse, synthetisieren aber kein aggregiertes Gesamt-Signal.
  Downstream-Consumer müssen die Aggregation selbst reimplementieren.
  *(Teilweise durch ChiefAgents-Plan adressiert — `docs/superpowers/plans/2026-06-04-chief-agents.md`)*
  **⚠️ Audit 2026-06-20 → in drei Teilen abgearbeitet (Eintrag bleibt offen bis beide PRs gemergt):**
  (a) `equity_chief` aggregierte bereits via `weighted_signal` (vor dem Audit erledigt).
  (b) `bond_chief` (eigenes Credit-Voting+Veto) → bewusst durch ein **Risikoaffinität-Modell** ersetzt (Veto entfiel) → **PR #19** (`feat/bond-risikoaffinitaet`).
  (c) `commodity_chief_agent_mikro` aggregierte **gar nicht** → **dieser PR**: `weighted_signal` über die 4 Sub-Signale (Supply/Demand 0.35, Bewertung 0.30, COT 0.20, Saisonalität 0.15 — Saisonalität bewusst am niedrigsten; `UNAVAILABLE` re-normalisiert), `overall_signal`+`confidence` im `CommodityBottomUpResult` + Event. 4 Tests; Suite 743 grün. *(PR: `fix/bug47-commodity-mikro-aggregation`.)*
  **Review-Feinschliff 2026-06-21:** Event-Payload trägt jetzt zusätzlich `confidence` (gerundet, analog `equity_chief`/`index_chief`) — Event-Consumer kennen die Urteilssicherheit, ohne sie nachzurechnen.
  **✅ Teil (c): PR #20 am 2026-06-21 gemergt** (Review ohne blockierende Mängel; im Review nur `confidence` ins Event ergänzt — siehe oben).
  → **Abhaken**, sobald **auch PR #19** (Teil b) gemergt ist — dann ist Bug #47 vollständig erledigt.

- [ ] **Folge-Aufgabe (aus Review PR #20, 2026-06-21)** — effektive Gewichtung im Produktions-Normalfall
  `commodity_chief_agent_mikro`: Ohne Supply-/COT-Adapter liefern beide Agenten `UNAVAILABLE` (0.35 + 0.20 fallen weg). Nach Re-Normalisierung bestimmen dann allein Bewertung (0.30) und Saisonalität (0.15) das Signal → **effektiv 67 % Bewertung / 33 % Saisonalität**. Damit trägt die bewusst niedrigst gewichtete, als „verrauscht" markierte Saisonalität im realen Default ein Drittel des Urteils. Mathematik korrekt, aber die austarierte Gewichts-Leiter kollabiert teilweise (Datenrealität, AGENTS.md §3).
  *Lösungsansatz (fachliche Entscheidung des Users nötig):* z. B. `confidence` deckeln, wenn alle **fundamentalen** Inputs (Supply/Demand + Bewertung) `UNAVAILABLE` sind, oder Saisonalitäts-Beitrag absolut begrenzen statt nur relativ. Vor Umsetzung mit User abstimmen.
  *Sekundär:* Event-Payload-Keys projektweit vereinheitlichen — equity/index nutzen `"signal"`, bond/commodity `"overall_signal"`. Eigener kleiner Aufräum-PR.

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

### agents/stock_deep_dive/index/index_price_agent.py (Zeile 78–79) — YTD-Basis-Konvention
- [ ] **YTD-Anker prüfen: erster Handelstag des Jahres vs. Vorjahres-Schlusskurs** *(Folge aus Bug #42, Review 2026-06-21)*
  Aktuell ist die YTD-Basis `close.iloc[ytd_idx]` = **erster Handelstag des laufenden Jahres** (z. B. 2.1.). Die in der Praxis gebräuchlichere YTD-Definition nimmt den **Schlusskurs des letzten Handelstags des Vorjahres** (`close.iloc[ytd_idx-1]`, 31.12.) — konsistent auch mit `_ago(...)`, das bewusst `idx-1` verwendet. Differenz = Kursbewegung über den Jahreswechsel (klein, aber ≠ 0; eine *stille* Abweichung im gemeldeten YTD).
  **Ansatz:** Erst fachlich entscheiden, welche Konvention gelten soll (ggf. Provider-Vergleich). Falls Vorjahres-Schluss: Basis auf `close.iloc[ytd_idx-1]` umstellen — der Guard `0 < ytd_idx < len` bleibt gültig (bei `ytd_idx==0` gibt es keinen Vorjahrespunkt → weiterhin None). TDD: Test ergänzen, der den **exakten** Basiskurs pinnt (nicht nur `is not None`), damit die Konvention festgeschrieben ist.

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

> **PR-Protokoll: Regime-Replay-Backtest Stufe 1 — PR #26 am 2026-06-22 gemergt** (Merge-Commit `da0659e8`).
> Validierung Makro/Regime Point-in-Time (ab 1960, USA) gegen Forward-S&P (A) + NBER (B); Spec/Plan unter
> `docs/superpowers/{specs,plans}/2026-06-22-regime-replay-backtest*`. **Im Review geändert:** Der
> Voll-Branch-Review fing einen echten **stillen Bug** (fehlende Forward-Kurse am Fensterrand wurden als
> −100 % statt „nicht auswertbar" gewertet → Trefferquote verzerrt) → behoben + getestet. Im zweiten Blick
> des Users 6 weitere Punkte nachgezogen: tautologischer Composite-Test → echter Vergleich; Harness
> adapterfrei (§1, Null-Objekt-Default + Stub-Verdrahtung im Composition-Root); `_price_on`-Performance
> (`end=` statt `period=`); `RISK_OFF` → `_RISK_OFF`; Treue-Test um bullischen Fall + Confidence-Vergleich
> erweitert; §3.1 Mean-Return + Voll-Lauf-Performance als Folge-Aufgaben (unten). Gesamtsuite **816 grün**.
> *(Dieser Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme — er braucht den Merge-Commit-Hash.)*

- [ ] Composite-Score + erkanntes Regime mit Datum speichern.
  Nach 3 Monaten prüfen ob das damalige Regime tatsächlich eingetreten ist.
  Falls nicht: Gewichte in `INDICATOR_WEIGHTS` oder Schwellenwerte in `_regime_from` anpassen.
  Echter Lernkreislauf: Vorhersage → Realität → Kalibrierung.

#### Folge-Aufgaben aus Review PR #26 (Regime-Replay-Backtest Stufe 1, 2026-06-22)
- [ ] **Mean-Forward-Return je Richtung in `evaluate_market` ergänzen (Spec §3.1).** Spec nennt als
  Plausibilitätscheck den „mittleren Forward-Return der bullish- vs. bearish-Calls"; aktuell liefert
  `evaluate_market` nur Hit-Rate + Wilson-CI. **Ansatz:** je Horizont die Returns nach Richtung
  (`regime_direction`) summieren/mitteln → `mean_ret_bullish`/`mean_ret_bearish` ins Report-Dict +
  `build_report_md`; ein bullisch-treffender Motor sollte bullish-Mittel > bearish-Mittel zeigen.
- [ ] **Voll-Lauf-Performance: FRED-Serien einmalig laden statt pro Stichtag (Spec §9).** Der
  Default-Loader ruft `get_series_as_of_date` pro Serie **pro Stichtag**, plus die 4 Sub-Signal-Agenten
  ziehen weitere FRED-Serien je Stichtag → grob mehrere tausend API-Calls für 1960→heute. **Ansatz:**
  je Serie einmal die volle (Vintage-)Reihe laden und lokal pro `as_of` schneiden (Caching im
  `HistoricalFredProvider` oder ein vorgelagerter Serien-Cache). Niedrige Prio (v1 läuft, nur langsam).

### PM: periodische + manuelle Komplett-Neuanalyse von Portfolio-Positionen (Idee 2026-06-21, eigener Spec später)
- [ ] **Im Portfolio-Manager pro Position eine volle Deep-Dive-Neuanalyse anstoßen — manuell (1-Klick) und automatisch im Hintergrund (~alle 30 Tage).**
  Querschnittlich (alle Anlageklassen) + braucht **Scheduling** (Hintergrundlauf) → **eigenes Feature mit eigenem Spec**, NICHT Teil des Bond-Risikoaffinität-Specs.
  **Abgrenzung:** Das ist die *volle* Neuanalyse (frische Markt-/Rating-Daten + ganzer Pipeline-Lauf) — zu unterscheiden vom *billigen Recompute* (nur Affinität ändern → Gesamtsignal aus gespeicherten Bausteinen neu rechnen), der im Bond-Spec steckt.
  **Fundament schon da nach Bond-Spec:** gespeicherte Recompute-Bausteine + persistierte Risikoaffinität pro Position/Analyse.
  **Ansatz später:** Trigger-Port (manuell + Scheduler), reuse des bestehenden Analyse-Pfads je Position; Ergebnis in History/Position aktualisieren. Spec: `docs/superpowers/specs/`.
  *(Entstanden aus dem Bond-Risikoaffinität-Brainstorm — siehe `docs/superpowers/specs/2026-06-21-bond-risikoaffinitaet-design.md` §8.)*

- [ ] **PM-Recompute-Trigger verdrahten (billiger Affinitäts-Wechsel)** — *Folge aus Bond-Risikoaffinität (Final-Review 2026-06-21).*
  Die reine Funktion `core/utils/bond_recompute.recompute_bond_signal(blocks, new_affinity)` ist gebaut + getestet, aber **noch nirgends im PM aufgerufen**. Spec §4.8 verlangt: im PM die Affinität einer Anleihe-Position ändern → Gesamtsignal sofort aus den gespeicherten Bausteinen neu rechnen → gespeicherte Affinität + Signal aktualisieren.
  **Offen:** der PM-Schreibpfad (Positions-Mutation + Persistenz-Update der zuletzt gespeicherten Analyse). **Ansatz:** `risk_affinity` einer Position setzen → letzte Analyse-Bausteine aus `analysis_memory` laden → `recompute_bond_signal` → `recommendation`/`risk_affinity` der Position/History aktualisieren. Verwandt mit dem PM-Komplett-Neuanalyse-Eintrag direkt darüber (billiger Recompute ≠ volle Neuanalyse).

- [x] **PR #19 Review-Nachbesserungen (Bond-Risikoaffinität) — erledigt 2026-06-21.** Befunde aus dem zweiten Blick auf PR #19 behoben:
  1. **Judgment-Verdrahtung:** `judgment_agent` baute `all_signals` nur aus Equity-Bausteinen → für Anleihen alle `None` → das neue `BondResult.overall_signal` trieb keine Empfehlung. Neu: `_bottom_up_signals()` nimmt das Anleihe-Gesamtsignal als 7. Slot mit (defensiv via `getattr`); Bond-Signal erscheint zudem im Urteils-/XAI-Prompt.
  2. **Cache-Round-Trip:** `result_cache._bond_result_out/_load_bond_result` verlor `overall_signal/confidence/risk_affinity/credit_band` → jetzt serialisiert + wiederhergestellt (None bleibt None).
  3. **Verfügbarkeit (§3.4):** Bond-Sub-Snapshots haben jetzt `status: SignalStatus`; metrics/duration/spread setzen `UNAVAILABLE` ohne Signal-treibende Daten. `bond_chief` schließt UNAVAILABLE-Komponenten aus der Aggregation aus; `save_analysis` lässt sie weg → **Live- und Recompute-Pfad konsistent**.
  4. **Typsicherheit:** `Position.risk_affinity` ist jetzt `RiskAffinity`-Enum (Spec §4.1), Provider wandelt um; Monitor gibt am Rand `.value` aus.
  5. **Aufräumen:** toter `AGGRESSIVE_ASSET_CLASSES`-Code in `recommendation.py` entfernt (nirgends referenziert; irreführender Name).
  *(TDD; Gesamtsuite grün. Der PM-Recompute-Trigger oben bleibt die offene Folge-Aufgabe.)*

---

## 6. TEST-LÜCKEN

- [ ] **RegimeDetector** — vollständig ungetestet (Scoring-Logik treibt jede Empfehlung an)
- [ ] **MoatAgent** — `_overall()`-Schwellenwerte, Score-Clamping, JSON-Parsing ungetestet
- [ ] **ValuationRangeAgent** — DCF, KGV-Multiple, EV/EBITDA-Formeln ungetestet
- [ ] **FundamentalsAgent** — `_score()` mit 7 Indikatoren ungetestet
- [ ] **Chief-Agent-Tests** — prüfen nur `isinstance(result, XxxResult)`, keine Logik oder Aggregation
- [ ] **BacktesterChiefAgent** — `backtester_context`-Einfluss auf Confidence nie getestet
- [ ] **ResultCache Bottom-Up Round-Trip** *(Folge aus Bug #1, Audit 2026-06-20)* — `save_bottom_up()` → `load_bottom_up()` ist nie als Round-Trip getestet; gerade die nachgereichten Felder `index`/`commodity_deep` waren der ursprüngliche Crash-Auslöser. **Ansatz:** `BottomUpResult` mit allen 13 Feldern befüllen, speichern, neu laden, Feld-für-Feld-Gleichheit asserten (Happy Path + leere Optionalfelder).
- [ ] **JudgmentOrchestrator-Konstruktor-Smoke-Test** *(Folge aus Bug #2, Audit 2026-06-20)* — der `judge`-Modus ist nur durch einen echten Lauf abgesichert; kein Test fixiert die 3-Argument-Signatur `(llm, bus, memory)`. **Ansatz:** `JudgmentOrchestrator(llm, bus, memory)` mit Fakes instanzieren und asserten, dass die Konstruktion ohne `TypeError` durchläuft (verhindert die Regression des früher fehlenden `memory`-Arguments).

---

## 7. CODE-QUALITÄT / TOTER CODE

- [x] **CI eingerichtet: GitHub-Actions-Workflow prüft jeden PR automatisch mit `pytest` (Python 3.12).** Bisher gab es nur den geplanten `background_runner` (tägliche Analyse), aber **keine** Test-Prüfung bei PRs. Neu: `.github/workflows/ci.yml` (Trigger `pull_request` + `push: master`; Feature-Branch-Pushes lösen keinen Doppellauf aus) + `requirements-dev.txt` (enthält `pytest`; **kein** pytest-asyncio nötig — die Tests nutzen `asyncio.run(...)`, 0 `@pytest.mark.asyncio`). **Dummy-API-Keys** im Workflow (keine echten Secrets): `config/settings.py` bricht beim Import hart ab, wenn `FRED_/ANTHROPIC_API_KEY` fehlen; die Tests mocken alle Datenquellen (Hexagonal-Ports), brauchen die Keys also nie für echte Calls. Verifiziert im sauberen Worktree (ohne `.env`, nur Dummy-Keys = CI-Umgebung) **808 grün**; CI-Lauf am PR ebenfalls grün.
  **PR-Protokoll (§5): PR #25 am 2026-06-22 gemergt** (Merge-Commit `fdb99b4`). Auf ausdrücklichen Wunsch des Users direkt gemergt (er hielt CI zunächst für eine reine Browser-Funktion; geklärt: GitHub Actions hat keinen An/Aus-Schalter — die Workflow-Datei im Repo **ist** die Aktivierung). *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*
  **Offene Folge-Aufgabe:** `config/settings.py` bricht beim **Import** ab, wenn Keys fehlen → das erzwingt die Dummy-Keys in der CI. Optional die Key-Prüfung aus dem Import-Zeitpunkt herauslösen (erst beim tatsächlichen Adapter-Aufbau prüfen), dann braucht die CI gar keine Platzhalter mehr.

- [x] **DB-Schema ins Repo (`db/schema.sql`).** Am 2026-06-20 angelegt und noch am selben Tag **autoritativ** ersetzt (echte Typen/PKs/Defaults aus `information_schema`/`pg_indexes` der laufenden Supabase-DB; *direkt auf `master`, bewusste Workflow-Ausnahme*). Lösung: 3 Tabellen (`analysis_memory`/`backtester_reports`/`portfolio_snapshots`), `id uuid DEFAULT gen_random_uuid()`, `timestamp timestamptz`, JSONB-Felder mit Defaults; `short_action` enthalten.
- [ ] **Fehlende Lese-Indizes (Performance).** In der DB existieren nur die PK-Indizes (auf `id`). Die Lese-Filter haben **keine** Indizes: `analysis_memory (ticker, timestamp)` (`load_history`) und `backtester_reports (backtester_type, timestamp)` (`load_latest_backtester_report`). **Ansatz:** je einen Index anlegen, z. B. `CREATE INDEX idx_analysis_memory_ticker_ts ON analysis_memory (ticker, timestamp DESC);` — und in `db/schema.sql` nachziehen. Niedrige Prio, solange die Tabellen klein sind.
- [ ] **Echtes Migrations-Tool/-Ordner** statt der manuell gepflegten Migrationshistorie am Dateiende von `db/schema.sql` (z. B. nummerierte `db/migrations/*.sql`). Niedrige Prio.
- [ ] `core/utils/statistics.py` (Zeile 4) — `Z_THRESHOLD = 2.5` wird nirgends verwendet; entfernen oder einbinden
- [ ] `tests/test_recommendation.py` (Zeile 6) — `_short_report()` definiert aber nie aufgerufen; entfernen
- [ ] `docs/code_review_2026-06-05.md` — Bug-Fixes Tasks 1–18 als ✅ markieren (alle abgeschlossen, Datei spiegelt das nicht wider)

### Robustheit & Beobachtbarkeit: Provider-Fehler zentral kapseln + loggen (Review PR #13, 2026-06-20)

- [ ] **Geteilten Fehler-Schutz-Helfer (`_safe`) einführen, Logging hineinlegen, projektweit ausrollen.**
  **Befund 1 (Duplikation, Review zu Bug #44):** Derselbe Schutz gegen Provider-Fehler — geworfene Exception **oder** als Wert zurückgegebene Exception → neutraler Default — ist in **~40 Dateien** kopiert, in 3–4 verschiedenen Schreibweisen: `def _safe(r, d)` in Chief-Agents/Orchestratoren (nach `asyncio.gather(return_exceptions=True)`), `try/except`+`isinstance(...)` in Sub-Agenten, lokales `_safe(v)`. Jede Verbesserung müsste man heute an ~40 Stellen einzeln nachziehen.
  **Befund 2 (Beobachtbarkeit):** Der Fehlerfall wird **still** verschluckt — ein echtes neutrales Ergebnis ist nicht von einem Datenquellen-Ausfall unterscheidbar (z. B. `recent_transactions=0` / `short_float_pct=None` sehen identisch aus, egal ob „echt nichts da" oder „API kaputt"). Steht in Spannung zu **Bug #46** („breites except schluckt Fehler still"). `import logging` existiert heute fast nur in `adapters/` (fred/finnhub/yahoo/ecb/claude/redis), in Agenten praktisch nicht.
  **Lösungsansatz (löst Logging + Dedup in EINEM Schritt; AGENTS.md §2 nennt `_safe(...)` selbst):**
  1. Helfer in `core/utils/` bauen: z. B. `await safe_provider_call(fn, *args, default=..., logger=...)` für Sub-Agenten (kapselt `try/except Exception` **und** `isinstance(result, Exception)` → `default`) sowie `safe_result(r, default)` für die `gather`-Entpackung in Chiefs/Orchestratoren.
  2. **Logging in den Helfer legen** (`logger.warning("<quelle> fehlgeschlagen für <ticker>", exc_info=True)`) → Ausfälle werden projektweit + einheitlich sichtbar, an genau EINER Stelle (kein Hand-Patchen von 40 Dateien).
  3. Inkrementell ausrollen (pro Agenten-Paket ein eigener PR), Tests je grün halten.
  4. **Eigener Branch ab `master`** (nicht auf `fix/bug44-…`); größeres Feature → kurzes Spec/Plan unter `docs/superpowers/` (AGENTS.md §5).
  *(Adressiert Punkt 1 [Logging projektweit] + Punkt 2 [`_safe`-Helfer/Dedup] aus dem PR-#13-Review; eng verwandt mit Bug #46. Als Folge-Aufgabe via **PR #14 am 2026-06-20 gemergt** ins Logbuch aufgenommen — die Aufgabe selbst bleibt **offen**.)*

### Architektur-Entscheidung: EDA-Event-Bus ohne Zuhörer (Stand 2026-06-19)

- [ ] **Entscheiden, ob/wann die Publish-only-EDA einen echten Subscriber bekommt.**
  ~40 Agenten publishen Fertig-Events (`*Ready`), aber **kein Code `subscribe`d** → der Bus liefert heute **keinen** Mehrwert (Daten fließen über Rückgabewerte/`result`/Persistenz). Hexagonal (Ports/Adapter) ist davon unberührt und trägt sich. Risiko: sieht event-getrieben aus, verhält sich wie Direktaufrufe (YAGNI).
  **Ansatz:** Entweder **einen** ersten echten Zuhörer bauen, damit EDA sich verdient — natürlicher Erst-Kandidat: **Frontend-Fortschritts-Stream** oder ein **Audit-/Erklärungs-Log**; ggf. **Redis-Bus** für verteilten Lauf (`adapters/event_bus/redis_bus.py`-Stub existiert) — ODER bewusst dokumentieren, dass die Publish-Seite reine Vorbereitung ist. **Nicht** rausreißen (billig zu behalten, teuer über 40 Agenten zu entfernen).
  > **Teilerfüllung (2026-06-22, Branch `feat/api-bridge-cockpit`):** Mit der API-Brücke (Cockpit-Flow) existiert jetzt **der erste echte Subscriber**: `InMemoryEventBus.subscribe_all(handler)` wird vom `WebSocketBroadcaster` genutzt, um alle `*Ready`-Events live an verbundene WebSocket-Clients zu streamen — der Bus liefert damit zum ersten Mal echten Mehrwert. **Verbleibend:** Redis-Bus für verteilte/Multi-Prozess-Szenarien (`adapters/event_bus/redis_bus.py`-Stub) + weitere Subscriber (Audit-Log, Kalibrierungs-Stream). Der Eintrag bleibt offen bis Redis-Bus und weitere Subscriber stehen.

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

### Frontend / API-Brücke (Cockpit-Flow) — v1 (2026-06-22)

**✅ Umgesetzt (Branch `feat/api-bridge-cockpit`):**
v1 der Web-API-Schicht für den Cockpit-Flow:
- `adapters/api/` + `app/server.py`: drei Endpunkte — `GET /api/cockpit` (letztes Ergebnis; `204` wenn noch keines), `POST /api/cockpit/run` (202 + `run_id`, startet Hintergrund-Task), `WS /ws/cockpit` (Live-Event-Stream während des Laufs).
- Eigene Serialisierung (`cockpit_to_dict`, `event_to_dict`); pro-Domäne-`status` (`"available"` / `"unavailable"`) als UNAVAILABLE-Kontrakt für das Frontend (Chief gecrasht/Default → `status="unavailable"`).
- `subscribe_all` am `InMemoryEventBus` (erster echter Subscriber — siehe EDA-Eintrag oben).
- Spec: `docs/superpowers/specs/2026-06-22-api-bridge-cockpit-design.md`, Plan: `docs/superpowers/plans/2026-06-22-api-bridge-cockpit.md`.
- TDD vollständig (Serialisierung, Event-Dict, subscribe_all, Broadcaster/Run, Endpunkte via TestClient).

**✅ PR #24 am 2026-06-22 gemergt** (nach zweitem Blick des Users). Im Review noch ergänzt: siehe Review-Fixes direkt unten. Verbleibende Folge-Aufgaben #3–#7 bleiben offen (weiter unten).

**Review-Fixes (PR #24, 2026-06-22):**
- ✅ **UNAVAILABLE ≠ NEUTRAL im Serializer:** `cockpit_to_dict` liefert für eine ausgefallene Domäne jetzt `signal=null` statt des erfundenen `"neutral"` (Default-Signal). AGENTS.md §3 / Spec §6: eine Quelle ohne Daten darf kein echtes Signal vortäuschen. Neuer Helfer `_domain(...)`; 2 neue Tests (`test_unavailable_domain_signal_is_null_not_neutral`, `test_all_unavailable_domains_have_null_signal`). Suite: 763 grün.
- ✅ **Logbuch-Hygiene:** die unten als „Minor-Aufräumen" notierten Typ-Hint- und Docstring-Punkte waren im finalen Code bereits umgesetzt → abgehakt (siehe dort).

**Offene Folge-Aufgaben:**

- [ ] **Kein Lock auf parallele Läufe (bewusste v1-Grenze):** ein zweiter `POST /api/cockpit/run` startet sofort einen weiteren Analysedurchlauf parallel.
  *Ansatz:* bei Bedarf `409 Conflict` zurückgeben, solange ein Lauf aktiv ist — Lauf-Status und `run_id` im `RunManager` halten, sodass `POST` prüfen kann ob bereits ein Lauf läuft.

- [ ] **Keine Persistenz des letzten Ergebnisses:** `GET /api/cockpit` gibt nach Server-Neustart `204` zurück (Ergebnis-Cache liegt nur im Arbeitsspeicher).
  *Ansatz:* reiches API-Snapshot-JSON nach jedem Lauf auf Disk ablegen und beim Start laden (analog zu `JsonDatedHistory`); optional Supabase-Persistenz.

- [ ] **Pro-Domäne-Konfidenz & feineres UNAVAILABLE:** `status` markiert heute nur „Chief gecrasht/Default"; die Tiles zeigen noch keine Konfidenz pro Domäne (commodity-Chief berechnet eine Konfidenz in `weighted_signal`, verwirft sie aber vor der Serialisierung).
  *Ansatz:* `confidence` + datenbasierten `status` (nicht nur Crash-Flag, sondern auch „wie viele Quellen tatsächlich verfügbar") pro Chief-Result mitführen und in `cockpit_to_dict` weitergeben.

- [ ] **Folgeschnitte — `bottomup`/`judge`-Endpunkte:** `GET /api/bottomup`, `POST /api/bottomup/run`, `WS /ws/bottomup` (inkl. Ticker-Parameter) nach demselben Muster wie der Cockpit-Flow; danach reiche Widget-Daten (Buffett, Big-Mac) als eigene Endpunkte.
  *Ansatz:* `RunManager`-Abstraktion ist bereits generisch gehalten; neuer Router je Flow, gleiche Broadcaster-/subscribe_all-Verdrahtung.

- [ ] **WS-Verbindungsreihenfolge — frühe Events können verloren gehen (Review PR #24, #3):** `POST /run` startet sofort; gestreamt wird nur an *bereits* verbundene WS-Clients (kein Replay/Buffer). Verbindet der Client erst nach dem POST, verpasst er frühe `*Ready`-Events (im Extremfall das terminale). Recoverbar über `GET /api/cockpit`.
  *Ansatz:* den Client-Vertrag „erst WS öffnen, dann POST" in Spec + Routen-Docstring festhalten; bei Bedarf einen kleinen Pro-Lauf-Replay-Puffer (letzte N Events je `run_id`) nachrüsten.

- [ ] **Zeitstempel im WS-Vertrag ohne Zeitzone (Review PR #24, #4):** `event_to_dict` liefert `timestamp` aus dem naiven `datetime.utcnow()` → ISO-String ohne `Z` (z. B. `2026-06-22T10:15:03`). Ein Frontend interpretiert das oft als *lokale* Zeit. Teil der projektweiten `utcnow`→`now(timezone.utc)`-Aufgabe (oben), aber hier vertragsrelevant: sobald der Stempel tz-aware ist, trägt das JSON automatisch `…+00:00`/`Z`.

- [ ] **`_broadcast_tasks` pro Lauf scopen (Review PR #24, #5):** das Task-Set im `RunManager` ist instanzweit; bei überlappenden Läufen (kein Lock) wartet Lauf A im `gather` auch auf B's Broadcast-Tasks. Kein Bug (Reihenfolge *innerhalb* eines Laufs bleibt korrekt), aber beim Nachrüsten des `409`-Locks bzw. Pro-Lauf-Trackings sollte das Set **pro `run_id`** geführt werden.

- [ ] **Fokussierter Unit-Test für „Fortschritt-vor-Terminal" im `RunManager` (Review PR #24, #6):** der `gather`-Zweig (Kern der Reihenfolge-Garantie) wird heute nur end-to-end über den Routes-Test abgedeckt; `test_execute_…` läuft mit einem Fake-Orchestrator ohne Publishes (leeres Task-Set). *Ansatz:* Fake-Orchestrator, der über den Bus publiziert → Assert: alle Fortschritts-Broadcasts vor dem terminalen `CockpitResultReady`.

- [ ] **Security vor Nicht-localhost-Deployment (Review PR #24, #7):** `POST /api/cockpit/run` ist ein unauthentifizierter Trigger für echte FRED-/Yahoo-Calls und (v1-gewollt) ohne Lauf-Lock. Auf `127.0.0.1` gebunden ok; **bevor** die API je über localhost hinaus exponiert wird (Repo wird öffentlich), zwingend: Auth + Rate-Limiting + Lauf-Lock (sonst Kosten-/Missbrauchs-Vektor durch unbegrenzte parallele Läufe).

- [x] **Minor-Aufräumen (aus Reviews):** ✅ `cockpit_to_dict`/`event_to_dict` mit `-> dict[str, Any]` annotiert (bereits im finalen Code); ✅ Docstring-Verweis auf §7 EDA-Eintrag in `subscribe_all` ergänzt; ✅ CORS-Konfiguration mit Kommentar versehen (Dev-CORS, credential-frei). **Verbleibend** → in den Security-Eintrag oben überführt: falls später Auth, `allow_credentials=True` + Origins einschränken.

---

## 8. DESIGN-ENTSCHEIDUNGEN (Frontend — docs/frontend_notes.md)

> **Status: am 2026-06-21 mit dem Nutzer entschieden** (Details im Frontend-Konzept `docs/superpowers/specs/2026-06-21-frontend-konzept.md` §6).

- [x] **Buffett-Widget:** Tabelle (Default) + Karte als Tab + **Drill-down** (10-J-Zeitreihe). *(2026-06-21, §6.3 — deckt die früheren Punkte „Karte vs. Tabelle" + „Drill-down" ab.)*
- [x] **Big-Mac-Refresh:** **automatischer Abruf** (geplanter CSV-Pull vom Economist-GitHub, Rückfall auf zuletzt gespeicherte Version; keine offizielle API). *(2026-06-21, §6.5.)*
- [x] **Bildschirm:** **Desktop-first**, responsive. *(2026-06-21, §6.2.)*
- [x] **Framework:** **React**. *(2026-06-21, §6.1 — überstimmt SvelteKit-Empfehlung; Begründung: chart-lastig + KI-gestützt → größtes Ökosystem + zuverlässigste KI-Codegenerierung.)*
- [x] **Echtzeit-Refresh:** **WebSocket (live)** von Anfang an; Server pollt die (abruf-basierten) Quellen und pusht an den Browser. *(2026-06-21, §6.4 — überstimmt Polling-zuerst.)*
- [x] **Daten-Health-Indikator** (x/y Quellen aktiv im Header, Klick → Quellenliste live/Stub/Fehler; pro Analyse „Datenbasis x/y Bausteine"). *(2026-06-21 aufgenommen, §6.6.)*

### Eingabe-/Ticker-Auflösung — fehlt komplett (Stand 2026-06-19)

- [ ] **Nutzer-Eingabe robust zu einem kanonischen Tickersymbol auflösen.**
  Heute nur `ticker.upper()` in `app/main.py` (CLI) → „apple"/„APPL" scheitern (nur „AAPL" funktioniert); keine Namens-/Fuzzy-Auflösung, kein Frontend.
  **Ansatz (Tool-Wahl wichtig):** Kern-Auflösung über eine **Symbol-Such-API** (Finnhub `/search`, FMP `/search`, Yahoo Symbol-Lookup) — deterministisch, liefert kanonisches Symbol + Börse. **KEIN LLM für die reine Auflösung** (Halluzinations-Risiko: falsches Symbol = falsche Analyse). Optional eine **LLM-Schicht nur für natürliche Absicht** („wie riskant ist apple gerade?" → Entität + Analyse-Modus extrahieren), die dann die Such-API füttert. Sauber als Port `SymbolSearchProvider` modellieren, Adapter dahinter (Hexagonal). *(Erweiterung fürs Futures-Redesign (§9): zusätzlich Hülle/Basiswert erkennen — „gold future" → `(precious_metal, future, GC)`.)*

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
- [x] **Konflikt-Agent (Folge-Block, short.md §18)** — **Erledigt, gemergt via PR #6 am 2026-06-20.**
  `ConflictResolution`-Modell + `DeepDiveResult.conflict_resolution`; `ConflictAgent` (`agents/conflict/`, LLM via `VERDICT:`-Zeile, Parse-Fehler → `HOLD`); bedingter Call im `judgment_orchestrator` (nur bei `conflict`); Persistenz (`conflict_verdict` + `conflict_reasoning`) + Anzeige. Im Review nachgebessert: HOLD-Fallback (kein Prosa-Scan), None-Guards, `ConflictResolutionReady`-Event. Spec/Plan: `docs/superpowers/{specs,plans}/2026-06-19-konflikt-agent*`.
  → Folge-Feature **Konflikt-UX (Inbox)** = eigener offener Punkt direkt darunter.
- [ ] **Konflikt-UX (Inbox + Entscheidungs-Protokoll)** — Folge des Konflikt-Agenten; **jetzt baubar** (Block #3 / PR #7 erledigt).
  **⚠️ VOR dem Bau `docs/short.md` §19 lesen — dort liegt der vollständige Design-Kontext + alle Brainstorm-Entscheidungen.** Das Logbuch hält hier nur den **Status**; das **Design lebt im Short-Hub** (`short.md`). Kurzfassung: Tool handelt nie selbst (zeigt Konflikt + fragt „halten/schließen?" + protokolliert nur die Antwort); persistente **Inbox** (offen → erledigt); Auslöser **on-demand + proaktiv**. Verdikt-Auswertung/Kalibrierung = Block #4.
- [ ] **Block #3 — Regeln/Regime-Weiche + Track-B-Hedge + Portfolio-Manager-Ausbau.** `portfolio_monitor_agent` hat **kein** `side`/`direction`-Feld (heute long-only).
  **Ansatz:** `side` (long/short) je Position in `portfolio.json`; short-bewusste P&L (invertiert) + Netto-Exposure; daraus `current_position` (none/long/short) ableiten; Reconciliation (beide Linsen feuern).
  - **3a in Review (PR #7, 2026-06-20):** `Position`-Modell + `PortfolioPort` + `JsonPortfolioProvider` + richtungs-bewusster Monitor (P&L/Exposure/Klumpen netto) + `current_position` aus dem Depot, CLI-`--position` entfernt. **Review-Befunde im Branch gefixt** (TDD, Gesamtsuite 709 grün): **F1** Alignment-Warnung jetzt richtungs-bewusst (short fehlausgerichtet bei COVER/BUY statt SELL/SHORT — Short+SHORT ist Ausrichtung, kein Fehlalarm mehr); **F2** englische Monitor-Kommentare auf Deutsch (AGENTS.md §0); **F3** `shares`/`buy_price` werfen wie `direction` `PortfolioError` (fail-loud konsistent); **F4** Monitor druckt Netto **und** Brutto getrennt. **PR #7 am 2026-06-20 gemergt** (Merge-Commit `dfda4b7`) — Review-Änderungen F1–F4 wie oben, Gesamtsuite 709 grün.
  - **F1-Nachbesserung (Nach-Merge-Review PR #7, 2026-06-20):** Die in PR #7 gefixte Short-Alignment-Warnung war *logisch* korrekt, **feuerte aber in Produktion nie** (Persistenzlücke): `save_analysis` persistierte nur die **Long**-Aktion unter `recommendation`; die Long-Linse deferiert bei Short-Positionen auf `NONE` → `COVER` landete nie in der History, der Short-Zweig matchte nie. Zudem waren `SHORT` (Long-Zweig) und `BUY` (Short-Zweig) vestigial (werden nie ausgegeben; `ShortAction` kennt kein BUY). **Fix (eigener PR, TDD, Gesamtsuite 711 grün):** (1) **`short_action` als eigene DB-Spalte** in `analysis_memory` persistiert (`result.short_action.value`, symmetrisch zu `recommendation`); (2) Monitor liest für Shorts `short_action` (feuert bei `COVER`), für Longs `recommendation` (feuert bei `SELL`); (3) vestigiale `SHORT`/`BUY` entfernt. **⚠️ Deploy-Schritt:** vor Merge/Deploy einmalig auf Supabase `ALTER TABLE analysis_memory ADD COLUMN short_action text;` ausführen, sonst schlägt jeder `save_analysis`-INSERT fehl. **PR #9 am 2026-06-20 gemergt** (Merge-Commit `7e6e2f2`) — Migration vorab ausgeführt (Spalte `short_action` in der DB verifiziert), Gesamtsuite 711 grün.
  - [ ] **Risiko-Kennzahlen verfeinern: Beta-/Korrelations-bereinigtes Netto-Exposure + ETF-Look-Through** *(Befund 2026-06-20 aus PR#7-Review, fachliche Folge von 3a — User-Einwand).*

    **Status & verbindliche Sequenz (2026-06-20) — NICHT vergessen:** in drei Schritte zerlegt:
    - **F4a — `net_beta` pro Region + `returns_provider`/Vola produktiv** → ✅ **umgesetzt** (Branch `feat/risk-net-beta-vola`, **PR #11**; Spec `docs/superpowers/specs/2026-06-20-net-beta-vola-design.md`). `net_beta = Σ(signed_value·β)` je Region als **$-Hedge-Notional**; Vola live.
      **Review-Nachbesserungen (PR #11, 2026-06-20, TDD, Gesamtsuite 727 grün):** (1) `net_beta` **nur** `equity`/`index` (Bonds/Rohstoffe/Edelmetalle raus — kein Aktienmarkt-Beta; ihr Risiko fängt die Vola ab); (2) `net_beta_pct`-Nenner = **Aktien-Brutto** (Äpfel/Birnen vermeiden); (3) Vola führt Renditen **per Datum** zusammen (`make_returns_provider` → datierte `pd.Series`, `DataFrame.dropna`) statt per Listenposition (Feiertags-Versatz); (4) Daten-Beschaffung **parallel** (`_gather_market_data`, `to_thread`+`gather`); (5) `market_provider: Optional[MarketDataProvider]`; (6) Risiko-Kennzahlen als **`metrics`-jsonb** persistiert + beim Laden entpackt. **PR #11 am 2026-06-20 gemergt** (Merge-Commit `9e34dda`); Migration vorab ausgeführt (`ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS metrics jsonb DEFAULT '{}'::jsonb;`, Spalte verifiziert). Folge-Block **F4c** (Nicht-Aktien-Hedges) siehe unten.
    - **F4b — ETF-Look-Through** ⬜ — braucht **Holdings-Quelle** (`get_index_holdings` ist Stub, überschneidet §5/Plan E).
    - **F4c — Nicht-Aktien-Hedges (instrumentengenau)** ⬜ *(geparkt aus PR-#11-Diskussion, eigenes Brainstorming offen)* — Bonds via **DV01/Duration** → Staatsanleihe-Future passender Laufzeit (Zinsrisiko; Kreditrisiko als Rest ausweisen); Rohstoffe **je Underlying** (eigener Future/ETF, nicht über Rohstoffe saldieren); Edelmetalle einzeln (GC/SI/…). **Voraussetzung:** DV01-Maschinerie (`core/utils/bond_math`) ist da, aber **`get_bond_data` ist Stub** (`{}`) → erst Bond-Datenquelle ODER ETF-effective-duration-Shortcut. Architektur-Skizze: „Hedge-Instrument-Registry" + Exposure-Rechner je Anlageklasse (verallgemeinert `net_beta`).
    - **Upgrade — Kovarianz-/Korrelationsmatrix** ⬜ (statt Einzel-Beta → optimale Hedge-Ratios; nutzt dieselben Renditereihen).

    **Gesamt-Reihenfolge des Shorts-Programms (ab hier):** **F4a** → **F4b (ETF-Look-Through)** → **SHORT+-Aktivierung** ✅ (durch 3a freigeschaltet; **erledigt, PR #21** — siehe Vermerk unten) → **3b Track-B-Hedge** (dimensioniert auf `net_beta`, pro Region der richtige Index) → **Block #4 Short-Backtest**. *(Roadmap zentral hier im Logbuch; `short.md` = nur Design.)*

    > **PR-Protokoll (§5): SHORT+-Aktivierung → PR #21 am 2026-06-22 gemergt** (Merge-Commit `e8ea821`). Aktiviert die bis dahin ungenutzte `ShortAction.SHORT_PLUS`: in einen **bereits gewinnenden** Short nachlegen (symmetrisch zu BUY+), mit zwei Short-Gates — Profit-Gate (`pnl ≥ 5 %`) + Squeeze-Gate (`squeeze ≠ high`); konservative Top-up-Tranche `_position_size_pct(conf)·0,25`, Stop 15 %. P&L kommt aus dem Depot über den per DI durch die Judgment-Kette (`Orchestrator → Chief → Agent`) injizierten `PortfolioPort`; die Engine (`core/domain/short_assessment.py`) bleibt eine pure function (neuer Parameter `position_pnl_pct=None`, verhaltens-erhaltend). Vollständig defensiv: fehlt Port/Einstand/Kurs → `None` → HOLD. **Review (zweiter Blick) — vier Befunde im Branch nachgebessert (TDD, Gesamtsuite 759 grün; Commits `64b3610`, `60434fb`):** **(1)** Ticker-Abgleich case-insensitiv in `position_state_for` **und** im P&L-Helfer (System-Ticker sind upper; sonst hätte SHORT+ bei abweichender CLI-/Depot-Schreibweise still nie gefeuert); **(2)** P&L-Helfer fängt zusätzlich `OSError`/`ValueError` (`JSONDecodeError ⊂ ValueError`) ab → kaputte `portfolio.json` lässt nur SHORT+ entfallen statt das ganze Urteil auf `default()` zu kippen; **(3)** `portfolio_port` durchgängig als `PortfolioPort | None` typisiert (Chief + Orchestrator); **(4)** P&L über **volumengewichteten** Durchschnitts-Einstand **aller** Short-Lots desselben Tickers (`Σ Einstand·Stück / Σ Stück`) statt nur des ersten Lots — sonst war das 5-%-Gate reihenfolge-/lotabhängig. Befund 5 (`elevated`-Squeeze erlaubt SHORT+) bewusst belassen (per Spec). Specs/Plan: `docs/superpowers/{specs,plans}/2026-06-21-short-plus*`. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*

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
- [x] **Track B — `ShortThesisAgent` (LLM)** — Fließtext-These + XAI auf der Engine. **Erledigt, PR #23 — siehe Vermerk unten.**

    > **PR-Protokoll (§5): Track B `ShortThesisAgent` → PR #23 am 2026-06-22 gemergt** (Merge-Commit `ad89290`). LLM-Agent (Muster `ConflictAgent`) erzeugt aus dem deterministischen `ShortAssessment` zwei Texte — `short_thesis` (angezeigt, analog `judgment`) + `short_xai` (persistiert in neuer Spalte `analysis_memory.short_xai`, analog `xai_explanation`); zwei sequenzielle LLM-Calls (These → XAI nutzt die These), vollständig defensiv (`("", "")`), vom `JudgmentOrchestrator` **immer** (null-sicher) aufgerufen. Migration `ALTER TABLE analysis_memory ADD COLUMN short_xai text;` vorab auf Supabase ausgeführt. **Review (zweiter Blick) — drei Punkte im Branch nachgebessert (TDD, Gesamtsuite 808 grün; Commit `4591916`):** **(1)** zwei fehlende **Fehlerpfad-Tests** im Orchestrator ergänzt (`short_assessment=None` → Agent nicht aufgerufen; Agent wirft → Felder leer, kein Crash — AGENTS.md §4); **(2)** `_assessment_block` weist fehlende Größe/Stop als `n/v` statt irreführendem `None%` im LLM-Prompt aus; **(3)** `bus.publish` **separat umhüllt** → ein Bus-Fehler verwirft die bereits berechneten LLM-Texte nicht mehr. Specs/Plan: `docs/superpowers/{specs,plans}/2026-06-22-short-thesis-agent*`. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*
- [ ] **Equity-Momentum-Agent (long + short)** — `MomentumSnapshot` (analog Index), aktiviert die dormanten Momentum-Flags. *(Equity hat noch keinen Momentum-Agenten.)*
- [ ] **Asset-Klassen-Shorts** — Rohstoff (Roll-Yield/Carry, Cost-Curve-Boden), Anleihe (Carry/Duration/Credit-Asymmetrie), Edelmetall. Je eigener Block.
- [ ] **Futures-Einbau via Taxonomie-Redesign (`underlying` × `wrapper`)** — Scope/Brainstorming **am 2026-06-21 abgeschlossen**; Design + Impact + Frontend-Konzept geschrieben. Statt einer „6. Klasse" ersetzen zwei Felder die `asset_class`: `underlying` (equity/equity_index/bond/commodity/precious_metal) wählt die Engine, `wrapper` (single/fund/future/physical_etc) schaltet eine Schicht zu. **Futures = `wrapper`, keine eigene Klasse.** Umfang Stufe 1: Rohstoff-/Edelmetall-Futures + physische Metall-ETCs.
  Specs: `docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md` (Design + §13-Entscheidungen) · `…-impact.md` · `…-frontend-konzept.md`.
  **PR-Protokoll (§5):** Spec-PR **PR #18 am 2026-06-21 gemergt** (Merge-Commit `a32433b`). Review (zweiter Blick): alle Code-Verweise gegen `master` verifiziert (stimmen), Finanz-Formeln nachgerechnet (korrekt). Im Review nachgebessert (Commit `9793a16`): (1) Frontend §1 an die §6-Entscheidungen angeglichen (React/WebSocket-live/automatischer Big-Mac statt der veralteten Svelte/Polling/manuell-Empfehlung); (2) „Mispricing"-Reste in Design §6.4/§11 auf die §13.4-Entscheidung (implizite Convenience-Yield vs. eigene Historie) korrigiert; (3) §11 klargestellt, dass die Phase-1-Regression nur für `wrapper ∈ {single, fund}` verhaltens-erhaltend ist und der `etf`-Reklassifizierungstest das **neue** Index-Ergebnis prüft. **Eintrag bleibt offen** — nur das Design ist gemergt, die 3 Umsetzungs-Phasen stehen noch aus.
  **Reihenfolge: erst Equity-Short fertig, dann Phase 1.** Umsetzung in 3 Phasen (je Spec→Plan→PR, TDD):
  - [ ] **Phase 1 — Taxonomie-Fundament** (verhaltens-erhaltend): `Underlying`/`Wrapper`-Enums; `BottomUpResult`, Orchestrator-Dispatch, `recommendation` (`_short_type`/Mengen + vollständige Aggressiv/Defensiv-Matrix), `short_assessment`-Weiche, `top_down_context`, `Position`, CLI; `index`→`equity_index`; XLE→`equity_index`, Rohstoff-/Minenaktien→`equity`; `etf`-Durchfall behoben.
  - [ ] **Phase 2 — Wrapper-Schichten + Daten-Ports (Long):** `FuturesCurveProvider` (+ Stub) → Kurve/Roll/Carry/Basis/Hebel/Verfall (Hebel-Deckel ≤ 10 % Nominal); `FundInfoProvider` (+ Stub) → TER + Tracking-Error (braucht Benchmark-Zuordnung); implizite Convenience-Yield aus Preisen (kein „Mispricing").
  - [ ] **Phase 3 — Long/Short-Feinschliff:** eigener Short-Zweig für `wrapper=future` (kein Borrow/Squeeze; Roll-Yield für Short; Cost-Curve-Boden als Deckel).
- [ ] **⚠️ Risiko-Kennzahlen auf Nominal umstellen — VOR Track-B-Hedge-Dimensionierung.** Futures-Hebel + physische ETCs verfälschen `net_exposure`/`net_beta` (rechnen heute mit Kapitaleinsatz statt Nominal); ein gehebeltes Buch sähe fälschlich „sicherer" aus. Exposure muss `wrapper`-abhängig auf den **Nominalwert** rechnen. *(Befund Impact-Analyse 2026-06-21; hängt mit der Risiko-Kennzahlen-Verfeinerung F4 oben zusammen.)*
- [ ] **NL-Resolver für Eingaben** („gold future" → `(precious_metal, future, GC)`) — erweitert die Ticker-Auflösung (§8) um Hüllen-/Basiswert-Erkennung; Such-API, kein LLM-Raten. Frontend-/Eingangsschicht, Folge-Aufgabe.
- [ ] **Borrow-Rate manuell** — optionales Eingabefeld als Ergänzung zum Hard-to-borrow-Proxy-Flag.
- [ ] **Index-Momentum-RS region/mutter-bewusst** (heute fix `URTH`): Sektor→Mutterindex, Land→Welt. Folge aus dem Equity-Momentum-Block (2026-06-22).
- [ ] **`_detect_crossover`/`_signal` des Index-Agenten auf `core/utils/momentum.py` dedupen** (Equity nutzt bereits die geteilten Helfer).

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
