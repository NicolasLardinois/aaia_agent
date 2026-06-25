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

- [x] **Bug #47** — `agents/stock_deep_dive/equity_chief_agent.py`, `bond_chief_agent.py`, `commodity_chief_agent_mikro.py`
  Chief Agents sammeln Sub-Agent-Ergebnisse, synthetisieren aber kein aggregiertes Gesamt-Signal.
  Downstream-Consumer müssen die Aggregation selbst reimplementieren.
  *(Teilweise durch ChiefAgents-Plan adressiert — `docs/superpowers/plans/2026-06-04-chief-agents.md`)*
  **✅ Audit 2026-06-20 → in drei Teilen abgearbeitet — alle drei gemergt:**
  (a) `equity_chief` aggregierte bereits via `weighted_signal` (vor dem Audit erledigt).
  (b) `bond_chief` (eigenes Credit-Voting+Veto) → bewusst durch ein **Risikoaffinität-Modell** ersetzt (Veto entfiel) → **PR #19** (`feat/bond-risikoaffinitaet`).
  (c) `commodity_chief_agent_mikro` aggregierte **gar nicht** → **dieser PR**: `weighted_signal` über die 4 Sub-Signale (Supply/Demand 0.35, Bewertung 0.30, COT 0.20, Saisonalität 0.15 — Saisonalität bewusst am niedrigsten; `UNAVAILABLE` re-normalisiert), `overall_signal`+`confidence` im `CommodityBottomUpResult` + Event. 4 Tests; Suite 743 grün. *(PR: `fix/bug47-commodity-mikro-aggregation`.)*
  **Review-Feinschliff 2026-06-21:** Event-Payload trägt jetzt zusätzlich `confidence` (gerundet, analog `equity_chief`/`index_chief`) — Event-Consumer kennen die Urteilssicherheit, ohne sie nachzurechnen.
  **✅ Teil (c): PR #20 am 2026-06-21 gemergt** (Review ohne blockierende Mängel; im Review nur `confidence` ins Event ergänzt — siehe oben).
  **✅ Teil (b): PR #19 am 2026-06-21 gemergt** (Merge-Commit `13eef3e`) — Credit-Veto durch Risikoaffinität-Modell ersetzt. Code-Beleg gegen `master` (2026-06-23): `bond_chief_agent.py:56` aggregiert via `aggregate_bond_signal(...)` und gibt `overall_signal`+`confidence` im `BondResult` zurück (Zeilen 64–68); Event trägt `overall_signal`.
  → **Damit Bug #47 vollständig erledigt** (alle drei Chiefs aggregieren ein Gesamtsignal: equity via `weighted_signal`, bond via `aggregate_bond_signal`, commodity-mikro via `weighted_signal`). Die separate Folge-Aufgabe „effektive Gewichtung" (unten) bleibt offen — sie ist ein eigenes Thema, kein Rest von #47.

- [ ] **Folge-Aufgabe (aus Review PR #20, 2026-06-21)** — effektive Gewichtung im Produktions-Normalfall
  `commodity_chief_agent_mikro`: Ohne Supply-/COT-Adapter liefern beide Agenten `UNAVAILABLE` (0.35 + 0.20 fallen weg). Nach Re-Normalisierung bestimmen dann allein Bewertung (0.30) und Saisonalität (0.15) das Signal → **effektiv 67 % Bewertung / 33 % Saisonalität**. Damit trägt die bewusst niedrigst gewichtete, als „verrauscht" markierte Saisonalität im realen Default ein Drittel des Urteils. Mathematik korrekt, aber die austarierte Gewichts-Leiter kollabiert teilweise (Datenrealität, AGENTS.md §3).
  *Lösungsansatz (fachliche Entscheidung des Users nötig):* z. B. `confidence` deckeln, wenn alle **fundamentalen** Inputs (Supply/Demand + Bewertung) `UNAVAILABLE` sind, oder Saisonalitäts-Beitrag absolut begrenzen statt nur relativ. Vor Umsetzung mit User abstimmen.
  *Sekundär:* Event-Payload-Keys projektweit vereinheitlichen — equity/index nutzen `"signal"`, bond/commodity `"overall_signal"`. Eigener kleiner Aufräum-PR.

- [x] **Flaky WS-Test stabilisieren** (`tests/adapters/api/test_routes_cockpit.py::test_ws_streams_until_terminal_then_get_returns_result`) — **gehört zur API-Brücke (PR #24).** Aktuell `@pytest.mark.skip` (sonst blockierte er die CI ~43 min, weil `ci.yml` bis dahin **kein** Test-Timeout hatte — letzteres ist jetzt behoben). Diagnose (CI-treuer Lauf mit Dummy-Keys): **zwei Races** — (1) **Registrierungs-Race** WS↔Broadcaster: feuert `POST /run` die Events, bevor der WS in `broadcaster.connect()` registriert ist, gehen sie verloren → `receive_json()` blockiert. *Lösungsvorschlag:* Subscription-Ack `{"type":"ready"}` direkt nach `connect()` in der WS-Route senden; Client (Test + Frontend) wartet darauf, bevor er `POST /run` schickt. (2) **Hintergrund-Task-Zustellung:** `RunManager.start_run` schedult `_execute` via `asyncio.create_task`; unter Test-Isolations-Druck (voller Suite-Lauf) wird der Task offenbar nicht zuverlässig auf demselben Loop zugestellt → die Run-Events kommen nie beim WS an. *Lösungsansatz:* den verschmutzenden Vorgänger-Test finden (asyncio-Loop-/Policy-Leak) bzw. die Zustellung deterministisch machen. **Prio: mittel** (Test isoliert grün; reine Integrations-Naht). *(Befund Review PR #28 / Fix-PR CI-Härtung, 2026-06-22.)*
  **Ergänzung 2026-06-23 (Befund PR #36):** Dieselbe Race-/Leak-Klasse trifft auch **zwei nicht-geskippte** Tests derselben Datei — `test_get_cockpit_is_204_before_any_run` und `test_post_run_returns_202_and_run_id` — die **nur im Gesamtlauf** (`python -m pytest -q`) umfallen, isoliert aber grün sind. Empirisch gegengecheckt: sie fallen **auch auf der merge-base** (ohne PR #36) → vorbestehend, nicht durch PR #36 verursacht. Gehören zum selben Fix (asyncio-Loop-/Policy-Leak des verschmutzenden Vorgänger-Tests). Damit ist die Folge-Aufgabe vollständig (3 betroffene Tests in `test_routes_cockpit.py`).
  **✅ Gelöst (2026-06-24, systematic-debugging — PR „test-isolation-access-token"):** Die obige „Zwei-Races"/„asyncio-Loop-Leak"-Diagnose war **falsch**. Wahre Ursache aller 3 Tests: **Env-Token-Leak bei der Collection** — `config/settings.py:4` ruft beim Import `load_dotenv()` auf; im Gesamtlauf zieht die Collection (`tests/test_cli_* → app.main → config.settings`) ein `AAIA_ACCESS_TOKEN` aus der lokalen `.env` prozessweit in `os.environ` → Auth **an** → token-loser WS-Connect wird mit Close `1008` abgewiesen und `POST /run` liefert `401`; das *sah* aus wie ein WS-Streaming-Race, war aber der fehlende Token. Beleg: Mit gesetztem `AAIA_ACCESS_TOKEN` fällt der Test **auch isoliert** deterministisch; ohne Token grün. Die zwei nicht-geskippten Tests wurden bereits in **PR #47** modul-lokal geheilt; dieser PR **konsolidiert** das auf **eine** Mechanik — paketweite `tests/adapters/api/conftest.py` (autouse, leert `AAIA_ACCESS_TOKEN` **und** `RENDER`) statt der bisherigen modul-lokalen `_auth_disabled`-Fixture (entfernt) — und **re-aktiviert den WS-Test** (Skip + ungenutzter `pytest`-Import entfernt). Produktionslogik (`run_manager`/Routen) **unverändert**. Verifiziert: voller Backend-Lauf grün, auch mit prozessweit gesetztem `AAIA_ACCESS_TOKEN`/`RENDER` (Worst-Case `.env`-Leak), WS-Test inklusive. Der tiefere, session-weite Schutz (Wurzel-`conftest`) bleibt als eigene Folge-Aufgabe offen (siehe „Test-Hermetik: ambiente `.env`-Secrets session-weit neutralisieren"). Falls je ein *echter* Registrierungs-Race auftauchen sollte, bleibt der Subscription-Ack (`{"type":"ready"}`) der dokumentierte Fallback. **PR #52 am 2026-06-24 gemergt.**

- [ ] **5 Agenten machen hardcoded Netzwerk-I/O statt injizierter Ports** (Verstoß AGENTS.md §1) — `put_call_agent` (`_fetch_cboe_put_call`/`-history`, CBOE via `requests`), `buffett_indicator_agent` (`_fetch_world_bank`, World-Bank — als Default-Arg `wb_fetch` gecaptured), `industrial_metals_agent` (`_fmp_price`, FMP), `bottom_up_backtester_agent` (`yfinance`), `portfolio_monitor_agent` (`_fetch_current_price`/`_default_fx_rate`, `yfinance`). **Folge:** Tests, die diese (über ihre Chiefs) laufen lassen, machten echte Calls → hingen in CI. **Zwischenlösung (umgesetzt, Fix-PR 2026-06-22):** `tests/conftest.py` blockt `requests`/`yfinance` global → die defensiven `except`-Pfade liefern Defaults → Suite offline-sicher (864 grün in 18 s statt ~3 min). **Eigentlicher Fix (dieser Punkt):** je Agent eine **injizierte Datenquelle** (Port + Adapter, real als Default, im Test gemockt) — dann fällt der `conftest`-Block weg und die Tests prüfen echte Pfade mit Fakes. **Prio: mittel** (Architektur-Hygiene; aktuell durch den Netz-Block abgesichert).

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

SNB — wired ist **`FredSnbProvider`** (`adapters/data/fred_snb.py`), nicht der `SnbStubProvider`.
**CH-Makro Slice A (PR #59 am 2026-06-25 gemergt):** Geldmengen/Bilanz/CPI via data.snb.ch, BIP/Yield via FRED. *(Review Claude: Quellen/YoY-Mathe + Caps verifiziert, defensiv/hexagonal, CI grün, keine Befunde.)*
- [x] `get_interest_rate()` — data.snb.ch (Cube `snboffzisa`, Reihe LZ) — bereits vorher angebunden
- [x] `get_m3_growth()` — data.snb.ch (Cube `snbmonagg`, D0=VV/D1=GM3 → YoY %)
- [x] `get_m2_growth()` — data.snb.ch (Cube `snbmonagg`, D0=VV/D1=GM2 → YoY %)
- [x] `get_balance_sheet_growth()` — data.snb.ch (Cube `snbbipo`, D0=T0 Bilanzsumme → YoY berechnet)
- [x] `get_cpi()` — data.snb.ch (Cube `plkopr`, D0=VVP → CPI YoY %; spiegelt BFS-LIK)
- [x] `get_gdp_growth()` — FRED `CLVMNACSCAB1GQCH` (reales BIP-Niveau → YoY berechnet)
- [x] `get_sovereign_yield_10y()` — FRED `IRLTLT01CHM156N`
- [ ] **Slice B — `get_core_cpi()`** — BFS Kerninflation (FRED-OECD-Serie `CPGRLE01CHM659N` ist 2025 eingefroren → nicht nutzbar; BFS px-web/LINDAS anbinden)
- [ ] **Slice B — `get_unemployment()`** — SECO/amstat (FRED-OECD `LMUNRRTTCHM156S` endet 2023 → unbrauchbar)
- [ ] `get_sovereign_yield_2y()` — keine freie 2J-CH-Quelle (bleibt None; im Spread via 3M-SARON-Proxy abgedeckt)

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

- [x] **`agents/stock_deep_dive/commodity/cot_agent.py`** — CFTC COT **angebunden** (PR offen, 2026-06-25).
  **Lösung:** neuer Adapter `adapters/data/cftc_cot.py` (`CftcCotProvider`, COTProvider-Port) liest die Disaggregated-Futures-Only-Managed-Money-Positionen über die CFTC-Socrata-API (Dataset `72hh-3qpy`); Managed-Money-Netto = long − short, plus Open Interest. Mapping Yahoo-Futures-Ticker → exakter CFTC-Hauptkontrakt (16 Rohstoffe, live verifiziert; bewusst der Yahoo-passende Kontrakt, z. B. NG=F = `NAT GAS NYME` Henry-Hub-NYMEX statt der größeren ICE-LD1-Reihe). Verdrahtung über optionales `cot_provider`-Argument: `BottomUpOrchestrator` → `CommodityChiefAgentMikro(cot_provider=…)` → `COTAgent`; in `app/main.py` mit `CftcCotProvider()` gesetzt. Ausfall/unbekannter Ticker → `[]` → `SignalStatus.UNAVAILABLE` (nicht-brechend). Live verifiziert: Gold 180 Wochen, Netto +113 721 / OI 339 330.

- [ ] **`agents/stock_deep_dive/commodity/supply_demand_agent.py` (Zeile 61)**
  EIA API (Öl/Gas), USDA (Agrar), LME (Metalle) nicht angebunden.

- [x] **`agents/market_cockpit/sentiment/fear_greed_agent.py`** — CNN Fear & Greed API **angebunden** (PR #34, 2026-06-23). **Lösung:** `adapters/data/cnn_fear_greed.py` (`CnnFearGreedProvider`), injiziert via `TopDownOrchestrator(sentiment=…)` in `app/main.py` + `app/server.py`; Ausfall/Strukturbruch → `WARNING`-Log → `None` → `UNAVAILABLE`. Redundanter `sentiment_stub.py` entfernt. (Siehe auch Plan-E-Eintrag unten.)
  > **PR-Protokoll (§5): PR #34 am 2026-06-23 gemergt** (Merge-Commit `0ad159a`). Mehrstufiges Review (pro Task + Opus-Whole-Branch) ohne blockierende Mängel; im Review nachgezogen: moderne Type-Hints, Test-Fake erbt vom Port, **WARNING-Log bei Ausfall** (Beobachtbarkeit). Erste Slice der „Stubs→echte Quellen"-Initiative. *(Dieser Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme — er braucht den Merge-Commit-Hash.)*

- [x] **Folge-Task (Review PR #34, 2026-06-23) — `fear_greed_agent.py`: 75er-Grenze vereinheitlichen.** **Erledigt 2026-06-25 (TDD).**
  Bei exakt `75.0` lieferte `_label` „Greed" (`<= 75`), `_signal` aber BEARISH (`>= 75`). **Lösung:** obere `_label`-Grenze auf `< 75` umgestellt → `75.0` labelt jetzt „Extreme Greed", konsistent mit dem Signal **und** dem offiziellen CNN-Band (75–100 = Extreme Greed). Schwellen-Begründung als Code-Kommentar ergänzt; 2 neue Grenz-Tests (75.0 = Extreme Greed + Label/Signal-Konsistenz; lückenloses Band 74.9/75.0/75.1). Suite 1168 grün. *(Eigener kleiner Agenten-PR — **PR #58 am 2026-06-25 gemergt**, Review Claude: lückenloses Band + Label/Signal-Konsistenz verifiziert, CI grün.)*

- [ ] **`agents/stock_deep_dive/equity/valuation_range_agent.py` (Zeile 55)**
  Vollständige Implementierung wartet auf Finnhub/FMP Adapter.

---

## 4. FEHLENDE EINZELFEATURES IN BESTEHENDEN AGENTS

### agents/market_cockpit/macro/inflation_agent.py

- [ ] **CPI Trend-Analyse** (`_signal()`, Parameter `trend` — reserviert, Zeile 20)
  `trend="rising"` soll Signal verschärfen, `trend="falling"` mildern.
  Benötigt: neue Provider-Methode `get_cpi_history(months=6)`.

- [x] **USA Core CPI** — FRED `CPILFESL` via `extended_state` angebunden (PR #62 am 2026-06-25 gemergt).
  In `inflation_agent` zusätzlich ins USA-`_signal` eingespeist (transiente Inflation entschärft BEARISH → NEUTRAL, konsistent zur EU). Live verifiziert: 2.82 %.

- [x] **USA PCE** — FRED `PCEPI` via `extended_state` angebunden (PR #62 am 2026-06-25 gemergt).
  Befüllt `InflationDataPoint.pce` (Fed-Ziel = PCE). Live verifiziert: 4.07 %. (Reines Anzeige-/Transparenzfeld, noch kein Signal-Input.)

- [x] **Eurozone Real Rate 10Y** — angebunden (PR #64 am 2026-06-25 gemergt; Merge-Konflikt mit #62 in isoliertem Worktree aufgelöst, betroffene Tests + CI grün. Review Claude: Fisher-Näherung + SR_10Y-Serie verifiziert, Realzins>2%→BEARISH konsistent zur USA, keine Befunde).
  Neue Port-Methode `EcbDataProvider.get_aaa_10y_yield()` (Default None), implementiert im `EcbSdwProvider` (Yield-Curve `SR_10Y`), durchgereicht vom `EurostatEcbProvider`. `inflation_agent` rechnet `eu_real_10y = ECB-AAA-10Y − EU-HICP` und speist es ins EU-`_signal` (Realzins-Gegenwind >2% → BEARISH, konsistent zur USA). Live verifiziert: 2.94 − 2.0 = 0.94 %.

- [ ] **Schweiz PPI** (`InflationDataPoint.ppi` für CH ist `None`)
  Quelle: SNB / BFS Erzeugerpreisindex.

### agents/market_cockpit/macro/interest_rate_agent.py (Zeile 77)
- [x] **FRED WALCL** — Fed Balance Sheet Growth angebunden (PR #62 am 2026-06-25 gemergt).
  `interest_rate_agent` holt jetzt zusätzlich `extended_state`; USA `balance_sheet_growth = ext.get("balance_sheet_growth")` (WALCL wöchentlich → YoY über 52 Wochen, QT negativ). Live verifiziert: +0.83 %.

### agents/market_cockpit/macro/gdp_agent.py (Zeilen 58, 70)
- [ ] **ISM Manufacturing PMI** für USA (`pmi=None`) — **deferred (keine freie Quelle).**
  FRED-Serie `NAPM` wurde eingestellt (existiert nicht mehr); ISM/S&P-Global-PMI sind proprietär (Lizenz). Wie EU-PMI deferred, bis eine lizenzierte/freie Quelle vorliegt.
- [ ] **procure.ch PMI** für Schweiz (`pmi=None`) — proprietär (procure.ch), deferred.

### agents/market_cockpit/macro/credit_agent.py (Zeilen 38–39)
- [ ] EU-Kreditwachstum via ECB API (aktuell immer NEUTRAL)
- [ ] CH-Kreditwachstum via SNB API (aktuell immer NEUTRAL)
  > **Eigener PR nötig (Folge-Aufgabe, 2026-06-25):** `credit_agent` (wie `labor_income_agent`) bekommt **nur** den USA-`MacroDataProvider` injiziert und wird auch im Backtester (`agents/backtester/regime_replay.py`, point-in-time) konstruiert. EU/CH erfordern: (a) **optionale** `ecb=None`/`snb=None`-Konstruktorargumente (rückwärtskompatibel — Backtester bleibt unverändert, EU/CH dort weiter NEUTRAL), Wiring nur im `macro_chief_agent`; (b) neue ECB/SNB-Datenmethoden: EU-Kredit via ECB-BSI (Kredite an privaten Sektor, YoY), CH-Kredit via data.snb.ch. Erst Datenquelle verifizieren, dann TDD.

### agents/market_cockpit/macro/labor_income_agent.py (Zeilen 38–39)
- [ ] EU-Löhne via Eurostat / ECB API (aktuell immer NEUTRAL)
- [ ] CH-Löhne via SNB API (aktuell immer NEUTRAL)
  > **Eigener PR nötig (Folge-Aufgabe, 2026-06-25):** wie credit_agent — optionale `ecb`/`snb`-Injektion (Backtester-kompatibel) + neue Datenmethoden: EU-Löhne via ECB „Negotiated wages"/Eurostat Arbeitskostenindex, CH-Löhne via BFS/SNB. Real-Lohn = nominal − CPI (Fisher), analog USA.

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

#### Regime-Kalibrierung Stufe ②-v1 — Risk-off-Grenze kalibrieren (2026-06-22, Branch `worktree-regime-calibration`)
- [x] **Stufe ②-v1 umgesetzt:** Walk-Forward-Kalibrierung der Risk-off-Grenze (`_REGIME_BIAS`) gegen NBER-Wahrheit (F1-Metrik).
  Spec `docs/superpowers/specs/2026-06-22-regime-kalibrierung-design.md`; Plan `docs/superpowers/plans/2026-06-22-regime-kalibrierung.md`.
  **Implementiert (5 Tasks):**
  Task 1: `_REGIME_BIAS`-Knopf + Trend-Invarianz in `core/domain/regime.py`.
  Task 2: `evidence["trend"]` + `urteil["trend"]` in `regime_replay.py`.
  Task 3: `bias_grid`/`f1_for_bias`/`best_bias_on` + NBER-Evaluator-Reuse in `core/utils/regime_calibration.py`.
  Task 4: `walk_forward`/`calibrate` (Expanding-Window, Markt-Härtetest A) ebenda.
  Task 5: `build_calib_report_md` (reiner String-Builder) + CLI `app/calibrate_regime.py` (NBER+FRED+yfinance, schreibt `data/backtests/regime_calib_YYYYMMDD.(json|md)`).
  **Kein Auto-Apply** — Urteil `adopt`/`keep_default` ist ein Vorschlag; `_REGIME_BIAS` wird manuell per PR gesetzt.
  > **PR-Protokoll: PR #33 am 2026-06-22 gemergt** (Merge-Commit `4d3e4ad`, CI grün). Im Review (zweiter Blick) noch
  > nachgezogen: A-Vorbehalt prüft jetzt die **Mehrheit der Horizonte** statt nur 6M (`_a_warning`); das `adopt`-Urteil
  > benennt bei gesetzter A-Warnung den Vorbehalt, statt nur „übernehmen" (Schein-Widerspruch gelöst); `evaluate_market`-
  > Import ans Modul-Top. Perf (`_price_on` pro Stichtag) ist durch das bestehende „Voll-Lauf-langsam"-TODO abgedeckt.
  > *(Dieser Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme — er braucht den Merge-Commit-Hash.)*
- [ ] **Stufe ②-v2: Gewichte kalibrieren (`INDICATOR_WEIGHTS` in `regime.py`).** Nächster Schritt nach ②-v1.
  **Ansatz:** gleiche Walk-Forward-Struktur, aber statt 1-D-Bias ein k-dimensionales Gewichts-Gitter (oder Bayes-Opt.) → eigener Spec nötig (Suche nach Gitter-Explosion, evtl. Random-Search oder Nelder-Mead).

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
- [x] **ResultCache Bottom-Up Round-Trip** *(Folge aus Bug #1, Audit 2026-06-20)* — **erledigt 2026-06-25** (`tests/adapters/test_result_cache_bottom_up_roundtrip.py`). Disk-Round-Trip (`save_bottom_up` → JSON → `load_bottom_up`) mit **befülltem** `index`+`commodity_deep` (die Bug-#1-auslösenden Felder, die der bestehende `test_taxonomy_model_roundtrip` auf `None` liess) + Gegenprobe (None bleibt None).
  **⚠️ Dabei echten latenten Bug gefunden + gefixt:** `_commodity_deep_out`/`_load_commodity_deep` verloren `overall_signal`+`confidence` (das in Bug #47 ergänzte Commodity-Gesamturteil) → beim Laden fielen sie still auf `NEUTRAL`/`0.0` zurück (**exakt** die Persistenz-Lücken-Klasse wie der Bond-Fix in PR #19). Serializer + Loader ergänzt; ältere Cache-Dateien fallen defensiv auf Defaults zurück.
- [x] **JudgmentOrchestrator-Konstruktor-Smoke-Test** *(Folge aus Bug #2, Audit 2026-06-20)* — **erledigt 2026-06-25** (`tests/test_judgment_orchestrator_construction.py`). Nagelt die 3-Argument-Signatur `(llm, bus, memory)`: Konstruktion mit den Pflicht-Argumenten läuft ohne `TypeError` und hält `memory` fest; ein `(llm, bus)`-Aufruf (der ursprüngliche Bug-#2-Crash) wirft jetzt nachweislich `TypeError`.
  > **PR-Protokoll (§5): PR #57 am 2026-06-25 gemergt** (beide Regressionsnetze oben). Review Claude: dabei echter latenter Persistenz-Bug (`overall_signal`/`confidence` im commodity_deep-Round-Trip, Klasse wie Bond-Fix PR #19) mitgefixt; defensiver None-Pfad verifiziert, CI grün, keine offenen Befunde.
- [ ] **Test-Hermetik: ambiente `.env`-Secrets session-weit neutralisieren** *(Folge aus PR #47, 2026-06-24)* — `config/settings.py` ruft beim **Import** `load_dotenv()` auf und kippt damit die echte lokale `.env` global in `os.environ` der gesamten Test-Session. Sobald irgendein Test `config` importiert, leckt z. B. `AAIA_ACCESS_TOKEN` (und potenziell `RENDER`) in alle folgenden Tests — genau der Cockpit-Isolations-Bug aus PR #47, dort modul-lokal via autouse-Fixture (`test_routes_cockpit.py`) geheilt. Jedes weitere Modul, das einen sauberen Env voraussetzt, kann von derselben Bug-Klasse getroffen werden. **Ansatz:** eine `autouse`-Fixture in der Wurzel-`conftest.py`, die sicherheitsrelevante Ambient-Variablen (`AAIA_ACCESS_TOKEN`, `RENDER`, ggf. weitere) im Testlauf leert, sodass die Einzelfixtures in `test_routes_cockpit.py`/`test_routes_auth.py` überflüssig werden. Verwandt mit der Import-Zeit-Nebenwirkung von `config/settings.py` aus §7 (Key-Prüfung beim Import herauslösen).

---

## 7. CODE-QUALITÄT / TOTER CODE

- [x] **CI eingerichtet: GitHub-Actions-Workflow prüft jeden PR automatisch mit `pytest` (Python 3.12).** Bisher gab es nur den geplanten `background_runner` (tägliche Analyse), aber **keine** Test-Prüfung bei PRs. Neu: `.github/workflows/ci.yml` (Trigger `pull_request` + `push: master`; Feature-Branch-Pushes lösen keinen Doppellauf aus) + `requirements-dev.txt` (enthält `pytest`; **kein** pytest-asyncio nötig — die Tests nutzen `asyncio.run(...)`, 0 `@pytest.mark.asyncio`). **Dummy-API-Keys** im Workflow (keine echten Secrets): `config/settings.py` bricht beim Import hart ab, wenn `FRED_/ANTHROPIC_API_KEY` fehlen; die Tests mocken alle Datenquellen (Hexagonal-Ports), brauchen die Keys also nie für echte Calls. Verifiziert im sauberen Worktree (ohne `.env`, nur Dummy-Keys = CI-Umgebung) **808 grün**; CI-Lauf am PR ebenfalls grün.
  **PR-Protokoll (§5): PR #25 am 2026-06-22 gemergt** (Merge-Commit `fdb99b4`). Auf ausdrücklichen Wunsch des Users direkt gemergt (er hielt CI zunächst für eine reine Browser-Funktion; geklärt: GitHub Actions hat keinen An/Aus-Schalter — die Workflow-Datei im Repo **ist** die Aktivierung). *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*
  **Offene Folge-Aufgabe:** `config/settings.py` bricht beim **Import** ab, wenn Keys fehlen → das erzwingt die Dummy-Keys in der CI. Optional die Key-Prüfung aus dem Import-Zeitpunkt herauslösen (erst beim tatsächlichen Adapter-Aufbau prüfen), dann braucht die CI gar keine Platzhalter mehr.

- [x] **DB-Schema ins Repo (`db/schema.sql`).** Am 2026-06-20 angelegt und noch am selben Tag **autoritativ** ersetzt (echte Typen/PKs/Defaults aus `information_schema`/`pg_indexes` der laufenden Supabase-DB; *direkt auf `master`, bewusste Workflow-Ausnahme*). Lösung: 3 Tabellen (`analysis_memory`/`backtester_reports`/`portfolio_snapshots`), `id uuid DEFAULT gen_random_uuid()`, `timestamp timestamptz`, JSONB-Felder mit Defaults; `short_action` enthalten.
- [ ] **Fehlende Lese-Indizes (Performance).** In der DB existieren nur die PK-Indizes (auf `id`). Die Lese-Filter haben **keine** Indizes: `analysis_memory (ticker, timestamp)` (`load_history`) und `backtester_reports (backtester_type, timestamp)` (`load_latest_backtester_report`). **Ansatz:** je einen Index anlegen, z. B. `CREATE INDEX idx_analysis_memory_ticker_ts ON analysis_memory (ticker, timestamp DESC);` — und in `db/schema.sql` nachziehen. Niedrige Prio, solange die Tabellen klein sind.
- [ ] **Echtes Migrations-Tool/-Ordner** statt der manuell gepflegten Migrationshistorie am Dateiende von `db/schema.sql` (z. B. nummerierte `db/migrations/*.sql`). Niedrige Prio.
- [x] `core/utils/statistics.py` — `Z_THRESHOLD = 2.5` wird nirgends verwendet; **entfernt** (2026-06-25). Beleg: kein Produktions-Import (`grep` über core/agents/adapters/orchestrators/app/tests = leer); die einzige echte Nutzung steht in `archive/anomaly.py`, das eine **eigene** lokale `Z_THRESHOLD`-Konstante hält (kein Import aus `statistics`). `ROBUST_Z_THRESHOLD` (der heute genutzte Iglewicz-Hoaglin-Schwellwert) bleibt. Statistik-Tests grün. *(eigener Cleanup-PR — **PR #56 am 2026-06-25 gemergt**, Review Claude: toter Code unabhängig bestätigt, CI grün, keine Befunde.)*
- [x] `tests/test_recommendation.py` — `_short_report()` toter Test-Helfer; **bereits entfernt** (2026-06-25 verifiziert: kein Treffer mehr in der Datei). Nur Logbuch-Nachzug.
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

- [x] `core/utils/relative.py` `_winsorize` — Guard bei `fraction >= 0.5` **ergänzt** (2026-06-25, TDD). Ab 0.5 überlappen die gekappten Tails (`lo_idx >= hi_idx`) → alle Werte kollabierten still auf einen Punkt. **Lösung:** `if fraction >= 0.5: raise ValueError(...)` (fail-loud, weil `fraction` ein Code-Parameter/Programmierfehler ist, kein Datenwert) + Docstring-Constraint. Verifiziert: kein Aufrufer übergibt ≥ 0.5 (alle nutzen 0.0/0.05). 3 neue Tests (≥0.5 wirft, knapp-unter-0.5 kappt sauber, `percentile_rank` reicht den ValueError durch). Suite 1169 grün. **PR #63 am 2026-06-25 gemergt** (Review Claude: Grenzfall verifiziert, CI grün).
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
- [x] **Doppelte Testdatei** `tests/domain/test_top_down_context.py` vs. `tests/test_top_down_context.py` — **konsolidiert 2026-06-25.** Beide testeten verschiedene Funktionen desselben Moduls (`_buffett_fallback_note` bzw. `derive_top_down_context`, keine Namens-Kollision). Alle 9 Tests im paketspiegelnden Pfad `tests/domain/test_top_down_context.py` vereint; die Root-Datei entfernt. Suite unverändert grün (kein Test verloren).

### Aus Plan D2 (Review 2026-06-17 — Logik korrekt, Daten fehlt)

- [ ] **SUE in Produktion aktivieren: `get_earnings_history` um `actual`/`estimate` erweitern** (`adapters/data/finnhub.py`).
  Die SUE-Logik (`core/utils/scoring.py` `standardized_unexpected_earnings`) ist korrekt + getestet, aber der Adapter liefert pro Quartal nur `beat`/`revision`, **kein `actual`/`estimate`** → SUE gibt produktiv immer `None` zurück; `earnings_trend_agent` läuft dann nur über die Revisionen (die Magnitude-Komponente fehlt).
  **Ansatz:** im Adapter pro Quartal `actual` (EPS-Ist) und `estimate` (EPS-Schätzung) befüllen — yfinance liefert diese via `Ticker.get_earnings_dates()` als `epsActual`/`epsEstimate`. Reihenfolge **älteste-zuerst** beibehalten (die SUE-Funktion nutzt das letzte = jüngste Quartal). Gehört zur Plan-E-Daten-Integration.

### Aus Plan E (Review 2026-06-17 — Ports/Logik gebaut, echte Datenquellen folgen)

- [ ] **Echte Datenadapter für die neuen Stub-Ports anbinden** *(die zentrale „Go-Live"-Aufgabe)*.
  Plan E hat Ports + Agenten-Logik gebaut; die Agenten liefern korrekt `UNAVAILABLE`, bis echte Quellen angebunden sind:
  - **COT** (`COTProvider`): CFTC Commitments of Traders (wöchentlich, CSV) → `adapters/data/cftc_cot.py`.
  - **Commodity Supply** (`CommoditySupplyProvider`): EIA (Öl/Gas), USDA (Agrar), LME (Metalle) → Lagerbalancen + Produktionskosten-Kurve.
  - [x] **Fear&Greed live angebunden** — `adapters/data/cnn_fear_greed.py` (`CnnFearGreedProvider`), injiziert in `app/main.py` + `app/server.py` via `TopDownOrchestrator(sentiment=…)`. **Lösung:** echter CNN-Adapter (0–100, Sanity-Cap, Browser-UA, verschachteltes JSON `fear_and_greed.score`); reine `_parse`-Funktion getestet; Fehler → `None` → `UNAVAILABLE`. Redundanter `sentiment_stub.py` entfernt (PR-Branch `feat/cnn-fear-greed`).
  - [x] **EU-Realwirtschaft (Eurostat) angebunden** — `adapters/data/eurostat.py` (`EurostatEcbProvider`, Decorator), injiziert via `ecb=EurostatEcbProvider(EcbSdwProvider())` in `app/main.py` + `app/server.py`. **Lösung:** HICP/Kern-HICP/PPI/reales BIP/Arbeitslosenquote via Eurostat (Jahresrate direkt; jüngste befüllte Beobachtung; geo EA20 bzw. EA21 für Arbeitslosigkeit); Sanity-Caps + WARNING-Logs; Fehler → `None` → `UNAVAILABLE`. Schaltet EU-Inflation komplett + EU-BIP (über Trend) scharf.
    > **PR-Protokoll (§5): PR #38 am 2026-06-23 gemergt** (Merge-Commit `75a7bba`). Schluss-Review (Opus) „Ready to merge: Yes". Im Review nachgezogen: Delegations-Test auf alle 8 Methoden, Kern-CPI-`unit`-Assertion, sparse-dict-Kommentar; Codes gegen Live-API verifiziert (EA20/EA21-Split). Slice 1 der Eurozone-Makro-Anbindung. *(Dieser Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme — er braucht den Merge-Commit-Hash.)*
  - [ ] **Folge-Task — EU-PMI** (gdp_agent): S&P-Global-PMI ist proprietär (keine freie API) → bleibt `UNAVAILABLE`; einen Fremdindex mit PMI-Schwellen zu nutzen wäre fachlich falsch. EU-BIP-Signal läuft solange über „BIP über Trend". Quelle/Lizenz klären.
  - [x] **EU-Geldmenge (Slice 2, ECB SDW) angebunden** — `ecb_sdw.py` liefert M2/M3-Jahreswachstum (BSI, verifiziert); `money_supply_agent` rechnet `eu_nom_gdp = reales BIP + CPI` (analog USA) → EU-Geldmengensignal scharf. Sanity-Cap + WARNING-Logs; Fehler → `None` → NEUTRAL. (CH-nom-BIP bleibt offen = spätere CH-Slice.)
    > **PR-Protokoll (§5): PR #50 am 2026-06-24 gemergt** (Merge-Commit `8e418e0`). Schluss-Review (Opus) „Ready to merge: Yes". Im Review nachgezogen: PEP-8 + Cap-Grenzwerte, Stub-Kommentar korrigiert, symmetrischer NEUTRAL-Test (fehlendes BIP). Geteilter `_parse_sdmx_last_observation`-Helfer (DRY, verhaltens-erhaltend); `_NullRegionProvider` im Replay um `get_gdp_growth`/`get_cpi` ergänzt. In isoliertem Worktree umgesetzt (parallele Session arbeitete am gleichnamigen Branch `feat/eu-geldmenge-ecb-sdw`). *(Dieser Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme — er braucht den Merge-Commit-Hash.)*
  - [ ] **Folge-Task (niedrig) — Eurostat-Caching** (Review PR #38): `EurostatEcbProvider` macht pro Analyse-Lauf 5 Live-Calls an Eurostat (kein Cache). Passt zum bestehenden Adapter-Stil (FRED/ECB/Yahoo ebenso); für ein häufig laufendes Dashboard evtl. später ein kurzer TTL-Cache (Tagesdaten ändern sich selten). Bewusst Folge-Thema, projektweit (nicht Eurostat-spezifisch).
  - **Index-Daten** (`MarketDataProvider.get_index_constituents` / `get_constituent_histories` / `get_index_fundamentals` / `get_index_holdings`) — aktuell Default-Stubs (leer).
  **Ansatz:** je Quelle einen Adapter implementieren, der die jeweilige Port-Methode befüllt; die Agenten schalten dann automatisch von `UNAVAILABLE` auf echte Signale (keine Agenten-Änderung nötig).
  *(`get_real_rate_history` (FRED DFII10) ist erledigt — siehe gemergte Realzins-/Zins-Adapter.)*
- **Total-Return-Historie: bewusst NICHT umgesetzt** (2026-06-18). Für die Schweizer Sicht ist Price Return (steuerfreier Kapitalgewinn) der passende Default; TR unterstellt steuerfreie Dividenden-Reinvestition (idealisierte Brutto-Benchmark, ignoriert Steuern). Der tote Haken (`get_total_return_history` im Port + TR-Vorzugslogik im `index_price_agent`) wurde entfernt.
- [x] `datetime.utcnow()` → `datetime.now(timezone.utc)` (DeprecationWarning unter Python 3.12). **Vollständig erledigt 2026-06-25.** Teilschritte: `core/domain/events.py` (tz-bewusster Default-Zeitstempel → löst zugleich den WS-Vertrags-Punkt unten) + `adapters/data/fred_api.py` (3× `utcnow().year`) umgestellt; Suite-Warnings von 256 → 1 gefallen. **Offen:** `adapters/cache/result_cache.py` (3 Stellen: `_is_fresh`-Vergleich + 2× `_saved_at`) — bewusst **separat** gelassen, weil (a) die Datei in PR #57 offen ist (kein doppelter PR auf derselben Datei) und (b) `_is_fresh` alte **naive** Cache-Dateien gegen neue **tz-aware** Stempel vergleichen muss (TypeError-Falle) → eigener kleiner PR mit naive/aware-Normalisierung + Test, **nach** Merge von PR #57. **PR #60 am 2026-06-25 gemergt** (events.py + fred_api.py; Review Claude: `.year` verhaltensgleich, WS-Stempel jetzt tz-aware, CI grün).
  **✅ result_cache.py-Rest erledigt 2026-06-25 (TDD, eigener PR):** `_is_fresh`-Vergleich + beide `_saved_at`-Schreibstellen auf `datetime.now(timezone.utc)` umgestellt. `_is_fresh` normalisiert alte **naive** `_saved_at`-Stempel defensiv auf UTC (`tzinfo is None → replace(tzinfo=utc)`), damit der Vergleich gegen das tz-aware `now()` nicht am naive−aware-TypeError scheitert (rückwärtskompatibel mit bestehenden Cache-Dateien). 4 neue `_is_fresh`-Tests (tz-aware frisch, alter naiver Stempel frisch, veraltet, fehlende Datei). **Damit ist die gesamte `utcnow`-Aufgabe abgeschlossen** — Suite-Warnings 256 → 0 (das letzte verbleibende stammt aus einem Test, der `utcnow` bewusst für den Rückwärtskompat-Fall erzeugt).
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

- [x] **Zeitstempel im WS-Vertrag ohne Zeitzone (Review PR #24, #4):** **Erledigt 2026-06-25** — der Default-Zeitstempel von `AgentEvent` ist jetzt `datetime.now(timezone.utc)` (tz-aware), daher trägt `event_to_dict(...)["timestamp"]` automatisch `+00:00`. Test `test_default_timestamp_isoformat_traegt_offset` nagelt das fest. *(Teil des `utcnow`→`now(timezone.utc)`-Cleanups, eigener PR — siehe §5 oben.)*

- [ ] **`_broadcast_tasks` pro Lauf scopen (Review PR #24, #5):** das Task-Set im `RunManager` ist instanzweit; bei überlappenden Läufen (kein Lock) wartet Lauf A im `gather` auch auf B's Broadcast-Tasks. Kein Bug (Reihenfolge *innerhalb* eines Laufs bleibt korrekt), aber beim Nachrüsten des `409`-Locks bzw. Pro-Lauf-Trackings sollte das Set **pro `run_id`** geführt werden.

- [ ] **Fokussierter Unit-Test für „Fortschritt-vor-Terminal" im `RunManager` (Review PR #24, #6):** der `gather`-Zweig (Kern der Reihenfolge-Garantie) wird heute nur end-to-end über den Routes-Test abgedeckt; `test_execute_…` läuft mit einem Fake-Orchestrator ohne Publishes (leeres Task-Set). *Ansatz:* Fake-Orchestrator, der über den Bus publiziert → Assert: alle Fortschritts-Broadcasts vor dem terminalen `CockpitResultReady`.

- [ ] **Security vor Nicht-localhost-Deployment (Review PR #24, #7):** `POST /api/cockpit/run` ist ein unauthentifizierter Trigger für echte FRED-/Yahoo-Calls und (v1-gewollt) ohne Lauf-Lock. Auf `127.0.0.1` gebunden ok; **bevor** die API je über localhost hinaus exponiert wird (Repo wird öffentlich), zwingend: Auth + Rate-Limiting + Lauf-Lock (sonst Kosten-/Missbrauchs-Vektor durch unbegrenzte parallele Läufe).

- [x] **Minor-Aufräumen (aus Reviews):** ✅ `cockpit_to_dict`/`event_to_dict` mit `-> dict[str, Any]` annotiert (bereits im finalen Code); ✅ Docstring-Verweis auf §7 EDA-Eintrag in `subscribe_all` ergänzt; ✅ CORS-Konfiguration mit Kommentar versehen (Dev-CORS, credential-frei). **Verbleibend** → in den Security-Eintrag oben überführt: falls später Auth, `allow_credentials=True` + Origins einschränken.

#### Zugriffsschutz (Branch `feat/access-protection`)

**✅ Umgesetzt:** Shared-Token (`AAIA_ACCESS_TOKEN`) schützt GET/POST/WS (Header bzw. `?token=`, constant-time; leer = Auth aus + Warn-Log, auf Render fail-closed); Lauf-Lock (`409`, `finally`-Freigabe); Frontend-Login-Gate (`useAuth`/`LoginGate`, localStorage, `401` → Passwortscreen, „Abmelden"); `render.yaml` + Deploy-Doku „Zugang für den Dozenten". Spec/Plan: `docs/superpowers/specs|plans/2026-06-22-access-protection*`. Backend-Folgeaufgabe #7 damit (für die Demo) **erledigt**.

**✅ PR #32 am 2026-06-23 gemergt** (nach zweitem Blick des Users). Im Review noch ergänzt: Logbuch-Konsolidierung (doppelte Überschrift entfernt), **Fail-closed auf Render** bei leerem Token (`RuntimeError` beim App-Bau statt still offen), 409-Route-Test.

**Offene Folge-Aufgaben:**

- [ ] **WS-Token als „erste Nachricht" statt Query-Param** (Log-Hygiene): der Token kann sonst in Server-/Proxy-Logs erscheinen. *Ansatz:* WS akzeptieren, erste Nachricht = Token, dann validieren/sonst schließen.
- [x] **Stiller fehlgeschlagener Lauf (Review PR #32):** wirft der Orchestrator, wird der Lauf-Lock korrekt freigegeben, aber **kein terminales Event** gebroadcastet → der WS-Client bleibt in „läuft". **✅ PR #36 am 2026-06-23 gemergt.** *Lösung:* terminales `CockpitRunFailed`-Event (Backend, generische Meldung — kein Leak; `latest` erst nach erfolgreicher Serialisierung) + Frontend-Fehlerzustand + `closeSocket`-Guard gegen Fehlalarm bei Verbindungsabbruch. *Im Review geändert:* bestehender `test_run_lock` an den neuen `_execute`-Vertrag angepasst (Fehler wird gefangen statt propagiert); 3 Coverage-Lücken + der `latest`-Serialisierungs-Edge-Case (`onEvent`/`onerror`/Payload-Fallback) ergänzt. *Folgeaufgabe:* 2 vorbestehende Flaky-Route-Tests bei der WS-Flaky-Aufgabe oben dokumentiert.
- [ ] **Echte Accounts / Rate-Limit** erst bei Bedarf (über die Dozenten-Demo hinaus).

### Frontend-Scheibe 1 — Cockpit-Übersicht (Branch `feat/frontend-cockpit-overview`)

**✅ Umgesetzt:**
React/TS/Vite/Tailwind-Frontend unter `frontend/`; Cockpit-Regime-Übersicht (Regime-Banner + 4 Domänen-Kacheln + Daten-Health + „Analyse starten"), live über `GET`/`POST`/`WS` (erst WS öffnen, dann POST); UNAVAILABLE-Vertrag (`signal=null`/Status) als gestreift-graues Feld; Basis-Komponenten (SignalBadge/ConfidenceBar/UnavailableField); pure Anzeige-Logik TDD-getestet; Render-Deploy als Static Site + `AAIA_CORS_ORIGINS` im Backend.
Spec: `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md`, Plan: `docs/superpowers/plans/2026-06-22-frontend-cockpit-overview.md`.

**✅ PR #27 am 2026-06-22 gemergt** (nach zweitem Blick des Users). Im Review noch geändert: (1) CORS-Hygiene — `AAIA_CORS_ORIGINS` **ersetzt** die Dev-Origins in Produktion (localhost nicht in der Prod-Allowlist) statt sie anzuhängen; (2) PR-Beschreibung ehrlich gemacht — sichtbar ist nur der „läuft …"-Status, der einzelne WS-Event-Stream wird gesammelt (Fundament), aber noch nicht gerendert. `as`-Cast-Guard und Effekt-Deps bewusst als Folge-Aufgabe/Nit belassen.

**Offene Folge-Aufgaben:**

- [ ] **WS-Reconnect/Replay:** bricht die WS-Leitung ab, fällt das Frontend auf `GET` zurück, aber ein laufender Lauf wird nicht weiterverfolgt.
  *Ansatz:* Reconnect mit Backoff + `GET`-Poll als Fallback; serverseitiger Pro-Lauf-Replay-Puffer (Backend-Folgeaufgabe #3) macht es robust.

- [ ] **Gerenderter WS-Fortschritts-Stream (aus Review PR #27):** der `useCockpit`-Hook sammelt die einzelnen `*Ready`-Events bereits im `events`-Array (Fundament), `CockpitPage` rendert sie aber noch nicht — sichtbar ist nur der „läuft …"-Status.
  *Ansatz:* in `RunControl`/`CockpitPage` eine kompakte Schritt-für-Schritt-Liste (z. B. „Makro fertig … Sentiment fertig …") aus `events` rendern; passt natürlich zur Reconnect/Replay-Aufgabe.

- [ ] **Drill-downs als nächste Scheiben** (Zinskurve/Buffett/Big-Mac): brauchen erst erweiterte Backend-Felder; eigene Spec/Plan je Scheibe.

- [ ] **Auth vor öffentlicher Render-Exposition:** verknüpft mit Backend-Folgeaufgabe #7 (Auth + Rate-Limiting + Lauf-Lock), bevor das Dashboard über localhost/privat hinaus erreichbar ist.

- [ ] **Charting-Bibliothek** (ECharts/Lightweight-Charts) erst mit den Drill-downs einführen.

- [x] **Aufräumen (aus Reviews):** ✅ ungenutzte Vite-Template-Reste entfernt (`App.css`, `assets/{react,vite}.svg`, `hero.png`, `public/icons.svg`); `index.html` auf Deutsch (`lang="de"`, Titel „AAIA — Cockpit"); `CockpitEvent.timestamp` optional (Terminal-Event trägt keinen). **Verbleibend:** `as unknown as CockpitOverview`-Cast im WS-Client später durch einen leichten Shape-Guard (Runtime-Validierung) ersetzen.

- [ ] **CI/Build-Reproduzierbarkeit:** Stack ist React 19 / TS 6 / Vite 8 / Vitest 4 (neuer als im Plan genannt); Node-/npm-Version in Render-Build + CI pinnen, damit die Lockfile-Auflösung reproduzierbar bleibt.

### Render-Deploy (Branch `feat/render-deploy`)

**✅ Umgesetzt:**
Blueprint `render.yaml` (Backend-Web-Service `aaia-api` via `uvicorn app.server:app --host 0.0.0.0 --port $PORT`, `numInstances:1`, Health `/api/cockpit`; Frontend-Static-Site `aaia-frontend`, `rootDir: frontend`, `staticPublishPath: dist`), `.python-version` (3.12), Anleitung `docs/deploy-render.md`. **Kein Code-Change** (Render nutzt den uvicorn-Start-Befehl; Secrets/URLs `sync:false`). Cross-URLs (`AAIA_CORS_ORIGINS`/`VITE_API_BASE_URL`) manuell im Zwei-Pass (Render `fromService` liefert keine öffentliche URL; Vite backt `VITE_API_BASE_URL` beim Build ein).
Spec: `docs/superpowers/specs/2026-06-22-render-deploy-design.md`, Plan: `docs/superpowers/plans/2026-06-22-render-deploy.md`.

**✅ PR #29 am 2026-06-22 gemergt** (nach zweitem Blick des Users; von Anfang an i.O., keine Review-Änderungen).
**✅ PR #30 am 2026-06-22 gemergt** (Nachtrag: `FMP_API_KEY` optional in `render.yaml` + Doku — vom User beim Deploy bemerkt; wird im Cockpit für LME-Zink/Nickel genutzt, ohne Key graceful `None`). Blueprint vom User in Render angewendet.
**✅ PR #35 am 2026-06-23 gemergt** (Deploy-Bugfix): Der Token-Schutz aus PR #32 hatte den Health-Check-Pfad `/api/cockpit` mit-gesperrt → Renders Health-Check pollt ohne Token → bekam `401` → Dienst galt als ungesund → Deploy `Timed Out`/`Failed` (Restart-Loop), obwohl die App lief. *Lösung:* öffentlicher `GET /healthz` (`200`, ohne Token), `healthCheckPath` darauf umgestellt; die echten Endpunkte bleiben tokengeschützt. TDD (29 API-Tests grün). **Backend danach live + von außen verifiziert:** `…/healthz` → `200 {"status":"ok"}`, `…/api/cockpit` ohne Passwort → `401`. Demo-Zugang (URL + Passwort) für den Dozenten damit bereit.

**Offene Folge-Aufgaben:**

- [ ] **Auth/Rate-Limiting/Lauf-Lock vor breiter Exposition (Backend-Folgeaufgabe #7):** verschärft sich, sobald die Render-URL erreichbar ist (`POST …/run` ist unauthentifiziert + ohne Lock; Repo öffentlich).
  *Ansatz:* API-Key-/Basic-Auth-Middleware + Rate-Limit am `POST …/run` + Lauf-Lock (`409` bei laufendem Lauf).

- [ ] **Cross-URL-Verdrahtung manuell (Zwei-Pass):** Render `fromService` bietet keine öffentliche URL.
  *Ansatz:* falls Render künftig eine URL-Property bietet, automatisieren; sonst beim Doku-Stand bleiben.

- [ ] **Ergebnis-Persistenz / Mehr-Instanz:** weiterhin offen (In-Memory) — Voraussetzung für Autoscaling.

### Frontend-Vollausbau — Slice 0 (Fundament + Shell, Branch `feat/frontend-vollausbau`)

**PR #40 am 2026-06-24 gemergt** (CLEAN, CI grün). Im Review drei Befunde nachgebessert (siehe Review-Nachtrag unten).

**✅ Umgesetzt:**
Router + App-Shell (Sidebar/Topbar mit Suche/Inbox-Badge/Health/Theme/Logout); Tausch-Naht-Fundament (`contract/common.ts`, `data/apiDeps.ts`, `data/dataMode.ts`, `DemoBadge`, `VITE_DATA_MODE`); pure Anzeige-Logik (assets/judgment/futures/curve/anomaly) TDD-getestet; gemeinsame Komponenten-Bibliothek (UnderlyingWrapperBadge, LongShortPanel, XaiPanel, AnomalyReport, SourceHealth, Schwellen-Badges); ECharts-Referenz-Wrapper (ChartContainer + LineCurve); Cockpit-Übersicht in die Shell eingehängt (Live-Anbindung unverändert, globaler Header/Logout jetzt in der Topbar). Spec: `docs/superpowers/specs/2026-06-23-frontend-vollausbau-design.md`, Plan: `docs/superpowers/plans/2026-06-23-frontend-slice0-fundament-shell.md`.

**Review-Nachtrag (PR #40):** drei Befunde behoben — (1) **SPA-Rewrite** in `render.yaml` (`routes: rewrite /* → /index.html`), sonst 404 bei Reload/Deep-Link unter BrowserRouter; (2) `rollYieldVisual` benennt die Kurvenform jetzt aus dem `form`-Argument statt aus dem Roll-Yield-Vorzeichen (kein stilles Mislabel bei Misch-/Übergangskurven, AGENTS.md §3) — +2 Tests; (3) Topbar-Suchfeld: Emoji aus dem Placeholder entfernt, `type="search"` + sauberer `aria-label` als Zugangs-Name (Placeholder nur noch Beispiel-Hinweis). 84/84 Tests grün, Build ok.

**Offene Folge-Aufgaben:**

- [x] **Slice 1 (Cockpit-Drilldowns)** — siehe Vermerk unten.
- [ ] **Slice 2–5 (Deep-Dive, Portfolio, Inbox, Backtester)** — je eigener Plan + PR; echte Backend-Endpunkte je Bereich (Tausch-Naht vorbereitet).

> **PR-Protokoll (§5): PR #44 am 2026-06-24 in `feat/frontend-vollausbau` gemergt** (Merge-Commit; MERGEABLE/CLEAN, CI grün, Frontend lokal 219/219 + Build ok). Slice 1 = alle Cockpit-Drilldowns (US3–US9) + Buffett/Big-Mac über die Demo-Tausch-Naht. Im Review (4 Befunde, alle im selben PR adressiert): (#2) Signal-Vertrag geklärt — Backend `InflationRow.signal` ist die einzige Wahrheit, `inflationBand().signal` nur Label, Konsistenz-Guard-Test; (#1) Buffett-Karten-Mapping `ISO3_TO_MAP_NAME` mit Guard-Test gegen stille graue Karte (Backend-Vervollständigung als Folgeaufgabe); (#3) Wortlaut „EU/DE→DE"; (#4) `world.geo.json` 987 KB als bewusste Entscheidung dokumentiert. *(Vermerk direkt auf `master`: bewusste Logbuch-Ausnahme; Detail-Logbuch liegt auf `feat/frontend-vollausbau` und fließt mit dessen Master-Merge nach.)*

### Frontend-Vollausbau — Slice 1 (Cockpit-Drilldowns, Branch `feat/frontend-slice1-cockpit-drilldowns`)

**✅ Umgesetzt (Dispatch A+B+C, 2026-06-23):**
Alle Cockpit-Drilldowns (US3–US9) über Demo-Naht (Tausch-Naht `useView`/`load*`/`demo/`):
- **Naht + Helfer (A):** Vertrag `contract/cockpit.ts`, generischer `useView`-Hook, pure `inflationBand` (USA/DE/CH, lückenlose Bänder), Tausch-Naht `data/cockpit.ts` + Demo-Fixtures `data/demo/cockpit.ts`, neue Chart-Wrapper `BarChart`/`buildBarOption` (Farbe nach Vorzeichen), `ChoroplethMap`/`buildMapOption` (Choropleth + grazilem GeoJSON-Fallback), pure Buffett-Logik `lib/buffett.ts` (Sortierung/Filter/vs-Median).
- **Drilldown-Seiten + Routing (B):** `DrilldownShell` (Zurück-Link, DemoBadge, SourceHealth); Makro/Rohstoffe/Sentiment/Zinskurve/Sektoren-Drilldown; klickbare Kacheln (`DomainTile` → Link); `routes.tsx` mit allen `/cockpit/<domain>`-Routen.
- **Spezial-Widgets (C):** `BuffettWidget` (Tabelle Default + Karten-Tab + 10-J-Drilldown + Filter onlyZOutlier/onlyBearish + analysiertes Land hervorgehoben + Global-Median + Einschränkungen); `BigMacWidget` (BarChart + Publikationsdatum); `/cockpit/buffett` + `/cockpit/big-mac` eingehängt. Schnellzugriff-Links in `CockpitPage` führen dorthin.
- TDD vollständig: 45 Test-Dateien, 204 Tests grün. `npm run build` erfolgreich.
- Plan: `docs/superpowers/plans/2026-06-23-frontend-slice1-cockpit-drilldowns.md`

**Offene Folge-Aufgaben:**

- [ ] **Echte Endpunkte je Drilldown-Bereich anbinden:** je Funktion in `data/cockpit.ts` die auskommentierte `fetch*`-Zeile aktivieren (`isDemo:false`). **Buffett ✅ erledigt** (2026-06-25, Branch `feat/cockpit-serializer-drilldowns` — Detail im Abschnitt „Drilldowns echt — Schritt 1" unten). Offen: Makro-Inflation, Rohstoffe, Sentiment, Zinskurve, Sektoren (teils Backend-Anreicherung nötig). Architektur-Erkenntnis: der Cockpit-Lauf rechnet die Detaildaten bereits — Engpass war nur der **Serializer** (`cockpit_to_dict` gab sie nicht aus) + ein **Detail-Endpunkt fehlt** (es gibt nur `/api/cockpit` mit dem Gesamt-Lauf, kein Endpunkt je Domäne).
- [x] **Welt-GeoJSON:** `frontend/public/world.geo.json` (987 KB, Apache-2.0, englische Ländernamen) liegt im Repo; `ChoroplethMap` registriert sie zur Laufzeit. Buffett-Karte joint per iso3→englischem GeoJSON-Namen (`toMapPoints` in `lib/buffett.ts`). In jsdom-Tests ist `fetch("/world.geo.json")` nicht auflösbar → Karten-Test prüft den Fallback (kein Produktionsproblem).
- [ ] **Inflations-UI: Core/PPI/Trend/Realzins-Modifikatoren spiegeln (optional):** `lib/inflation.ts` bildet nur die CPI-Bänder ab; Backend `inflation_agent` hat zusätzliche Modifikatoren. Bei Bedarf als weiterer Indikator im Makro-Drilldown zeigen.
- [ ] **Slice-0-Followup: LoginGate/Sidebar-Tests flakig unter paralleler Last** — unter der vollen Suite (45 parallele Test-Dateien) können `LoginGate`/`Sidebar`/`AppShell`-Tests gelegentlich durch I/O-Verzögerungen in Vitest (jsdom) einen Timeout treffen. Kein Logik-Fehler; tritt isoliert nicht auf. *Ansatz:* globales `testTimeout` in `vitest.config.ts` auf 15 000 ms erhöhen, oder flakige Tests mit `{ timeout: 15000 }` absichern; alternativ parallele Umgebungsanzahl begrenzen (`maxConcurrency`).

### Frontend-Vollausbau — Slice 2 (Deep-Dive, Branch `feat/frontend-slice2-deepdive`)

- [x] **Frontend Slice 2 — Deep-Dive** (Konzept §2.2/§2.3/§2.7, Spec §7). Lösung: Deep-Dive pro Anlage über die Tausch-Naht `loadDeepDive(ticker)` (Demo-Fixtures AAPL/GC=F/TLT/SPY/CL=F/4GLD + notFound). Header (underlying×wrapper + Kurs/Markt + vergleichen), LongShortPanel + XAI + Schwellen-Flags + AnomalyReport, kontextabhängige Tabs je underlying (equity/bond/index/commodity, Futures nur bei wrapper=future) über pure Tab-Registry `tabsFor`, Sub-Agenten-Health, Cockpit-Wind (US12), Backtest-Kontext (US21), Vergleichsmodus `?vergleich=<TICKER>` (US11), Routing `/deep-dive/:ticker` verdrahtet. Pure getestete Logik: `combineValuationRange`/`valuationPosition`, `altmanClass`, `durationRisk`, `tabsFor`. US10–22 + US33–36 abgedeckt. Frontend-Suite grün, `npm run build` erfolgreich. **PR #45 am 2026-06-24 gemergt** — nach `master` (Base beim Merge vom veralteten Stapel-Branch `slice1` auf `master` umgestellt, da `slice1`/`vollausbau` 108 Commits hinter `master` lagen; #45 mergte konfliktfrei, 287/287 Tests grün). Im 2. Blick wurden 4 Review-Befunde behoben (siehe Unterpunkt).
  - [ ] **Folge: echte Deep-Dive-Endpunkte** — `data/api/deepdive.ts` (`fetchDeepDive`) statt Demo; Naht-Zeile in `data/deepdive.ts` tauschen (Backend liefert underlying/wrapper, Long+Short+XAI, Futures-Roll-Kennzahlen, Sub-Agenten-Health). Lösungsansatz: bestehende stock_deep_dive-Chiefs (equity/bond/index/commodity/precious) hinter einen API-Endpunkt hängen, der den DeepDiveView-Vertrag erfüllt.
  - [ ] **Folge: COT/Saisonalität/Earnings-Trend echt** — aktuell teils UNAVAILABLE/Demo; an echte Quellen anbinden (siehe Stubs-Initiative im Logbuch).
  - [x] **Review-Befunde PR #45 (2. Blick) behoben:** (1) **Tab-Reset-Crash** — `DeepDivePage` behielt den aktiven Tab über einen Ticker-Wechsel (gleiche Route-Instanz); ein equity-only Tab wie „Qualität" dereferenzierte bei Wechsel auf z. B. TLT/bond einen leeren Block → Laufzeit-Crash. *Lösung:* `current` gegen die aktuelle `tabsFor`-Menge absichern (Fallback erster Tab) + Regressionstest mit echter In-App-Navigation. (2) **„vergleichen"-Button ohne sinnvollen Partner** — fiel blind auf `4GLD` zurück (von AAPL → Gold-ETC sinnlos). *Lösung:* Button nur bei vorhandenem Gegenstück desselben Basiswerts; zusätzlich Guard in `CompareView` (verschiedene `underlying` → Hinweis statt Tabelle). (3) **Zahlenformat** durchgängig auf deutsches Format (Komma/Tausenderpunkt) via neuem `lib/format.ts` `formatNumber`/`formatSigned` (TDD); alle Deep-Dive-Anzeigen + Tests angepasst. (4) **Altman-Sektor-Mapping** als bewusst grobe Backend-Parität im Kommentar dokumentiert (Label-Parität beim Echt-Anschluss verifizieren).

### Frontend-Vollausbau — Slice 3 (Portfolio, Branch `feat/frontend-slice3-portfolio`)

- [x] **Frontend Slice 3 — Portfolio (Track B)** (Konzept §2.4, Spec §7/§10 US23–27). Lösung: Portfolio-Bereich über die Tausch-Naht `loadPortfolio()` (Demo-Fixture: Positionen long+short quer über underlying×wrapper inkl. Konflikt-Fall XLE long+SELL). Positionstabelle mit Doppel-Etikett, L/S, Größe, Einstand, AAIA-Urteil + Konflikt-Markierung, Ticker→Deep-Dive (US23); Exposure-Panel Brutto/Netto/net_beta (aktien-only, datierte Vola) mit Inline-Definitionen (US24); Klumpen-Warnungen Sektor/underlying/Geographie mit Limit-Bezug (US25); beratende Hedge-Vorschläge ohne Ausführung (US26/US27). Pure getestete Logik (gespiegelt aus portfolio_monitor_agent/PR #11): `grossExposure`/`netExposure`/`netBeta`, `detectKlumpen`, `detectConflict` (exportiert → Slice 4 nutzt sie wieder), `hedgeSuggestions`. UNAVAILABLE-Pfad: Aktie mit Beta `null` zählt nicht ins net_beta; Beta-Feed-Stub als `failed`-Quelle. **Review-Nacharbeit (PR #48):** (1) **net_beta jetzt `number | null`** — wenn KEINE verwertbare Aktien-Beta-Position existiert (z. B. Beta-Feed komplett aus), ist net_beta UNBEKANNT → `null` (UNAVAILABLE im Panel), nie mehr fälschlich „0 %" (= „marktneutral"); deckt AGENTS.md §3 (UNAVAILABLE ≠ 0). (2) **Hedge-Schwelle symmetrisch** — `|net_beta| > 30 %`: stark net-LONG → Index-Short/VIX, stark net-SHORT → Index-Long/Teil-Eindecken (Rally-Risiko); `null` ⇒ kein Vorschlag. (3) Kosmetik: unnötiger Cast in `PositionsTable` durch saubere Typisierung (`LongVerdict | ShortVerdict`) ersetzt. Frontend-Suite grün (327 Tests), `tsc --noEmit` + `npm run build` erfolgreich. ✅ **PR #48 am 2026-06-24 nach master gemergt** (Merge-Commit `052f69b`; inkl. Review-Nacharbeit). Hinweis: PR war zwischenzeitlich durch Löschung des gestapelten Base-Branches `feat/frontend-slice2-deepdive` auto-closed; Base auf `master` umgestellt, reaktiviert und gemergt.
  - [ ] **Folge: echter Portfolio-Endpunkt** — `data/api/portfolio.ts` (`fetchPortfolio`) statt Demo; Naht-Zeile in `data/portfolio.ts` tauschen. Lösungsansatz: `portfolio_monitor_agent`-Snapshot (net_beta/Exposure/cluster_risks/Vola) hinter einen API-Endpunkt hängen, der den `PortfolioView`-Vertrag erfüllt; Klumpen-Limits aus dem Agenten (0.40/0.60/0.70) übernehmen.
  - [x] **Folge: Slice 4 (Inbox) verdrahten** — erledigt in Slice 4 (siehe unten): `detectConflict`/`conflictNote` zentral wiederverwendet, Inbox-Badge aus `openCount` gespeist.

### Frontend-Vollausbau — Slice 4 (Konflikt-Inbox, Branch `feat/frontend-slice4-inbox`)

- [x] **Frontend Slice 4 — Konflikt-Inbox** (Konzept §2.5, Spec §7/§10 US28–30). Lösung: Inbox über die Tausch-Naht `loadInbox()` (Demo-Fixture leitet die Konflikte aus dem wiederverwendeten `detectConflict`/`conflictNote` aus `lib/conflict.ts` ab — eine Quelle der Wahrheit, konsistent zum Portfolio-Demo: XLE long+SELL→EXIT, GC=F long+SHORT→REVERSE, TSLA short+BUY→REVERSE). `ConflictCard` zeigt beide Urteile (gehalten vs. neu), das beratende Verdikt **EXIT/HOLD/REVERSE** mit hervorgehobenem Default (`suggestVerdict`, US29) + Begründung, Querlinks Portfolio + Deep-Dive (§3); `InboxPage` mit **Offen/Erledigt-Tabs** + clientseitiger Abarbeitung (gefolgt/ignoriert/vertagt, Erledigt-Tab = Audit-Trail, US30); **keine Trade-Ausführung** (US27-Prinzip). **Topbar-Badge** echt verdrahtet: `AppRoutes` lädt `openCount(loadInbox)` und reicht `inboxCount` an `AppShell` durch (US28) — `useCockpit`-Live-Anbindung unberührt. Pure getestete Logik `suggestVerdict`/`openCount`. Frontend-Suite grün, `npm run build` erfolgreich. **PR #51 am 2026-06-24 gemergt** — nach `master` (Base beim Merge vom inzwischen gemergten Stapel-Branch `slice3` auf `master` umgestellt; #51 mergte konfliktfrei als Merge-Commit, 372/372 Tests grün). Im 2. Blick wurden 3 Review-Befunde behoben (siehe Unterpunkte: Kopf-Auslöser, A11y-Chips, Badge-Test).
  - **Hinweis (Vorfall):** Während Dispatch B beendete das Sitzungs-Limit einen `git commit` mitten im Ref-Write → der Branch-Ref `feat/frontend-slice4-inbox` wurde mit Null-Bytes überschrieben (HEAD nicht auflösbar). Wiederhergestellt aus dem Reflog (Tip `1897cb2`, keine Daten verloren); zwei ungenutzte-Import/Variable-`tsc`-Fehler (vitest meldet sie nicht) nachträglich behoben.
  - [ ] **Folge: echter Inbox-Endpunkt** — `data/api/inbox.ts` (`fetchInbox`) statt Demo; Naht-Zeile in `data/inbox.ts` tauschen. Lösungsansatz: gehaltene Positionen × aktuelles AAIA-Urteil serverseitig gegen `detectConflict` prüfen und als `InboxView`-Vertrag liefern.
  - [ ] **Folge: Status-Persistenz** — Offen/Erledigt-Status lebt aktuell nur im Komponenten-State (Reset bei Reload). Ansatz: Entscheidungen serverseitig/lokal persistieren (Audit-Trail dauerhaft).
  - [ ] **Folge: WebSocket-Push** — Inbox-Badge proaktiv aktualisieren, sobald ein Urteil zu einer gehaltenen Position kippt (statt nur beim Laden).
  - [x] **Folge (Minor, Whole-Review): Kopf-Auslöser bei long-Konflikt via Short-Signal** — `ConflictCard` zeigte im Kopf für long-Positionen `newLongVerdict`; bei GC=F (long, newLong=HOLD, newShort=SHORT) war der eigentliche Auslöser aber das SHORT-Signal. Lösung (PR #51-Review): neue pure Funktion `conflictTrigger(direction, judgment)` in `lib/conflict.ts` liefert das *auslösende* Urteil (long: SELL bzw. gegenläufiges SHORT; short: COVER bzw. gegenläufiges BUY); `conflictNote` baut jetzt darauf auf, und der Kartenkopf zeigt `conflictTrigger` (+ Farbe) — eine Quelle der Wahrheit, Kopf/Note/Vorschlag stimmen überein. TDD: `conflictTrigger`-Grenzfälle + GC=F-Kopf-Test (zeigt SHORT statt HOLD).
  - [x] **Folge (Minor, PR #51-Review): A11y der Verdikt-Chips** — die Vorschlag-Chips waren `role="button"` + `aria-pressed`, obwohl sie reine, nicht-klickbare Anzeige sind (Screenreader kündigte einen funktionslosen Toggle-Button an). Lösung: `role="group"`-Container, Default via `aria-current="true"` markiert; nur die echten Protokoll-Aktionen bleiben Buttons. Tests entsprechend umgestellt.
  - [x] **Folge (Minor, PR #51-Review): Badge-Routing-Test robuster** — der Test prüfte `queryByText("3")` global (könnte zufällig eine andere „3" treffen). Lösung: Assertion auf die Inbox-Navigation (`aria-label="Inbox"`) gescopt; die Badge-Zahl muss im Inbox-Link stehen.
  - [ ] **Folge (Minor, Whole-Review): Demo-Querlink-Drift Inbox↔Portfolio** — GC=F/TSLA sind in der Inbox-Demo Konflikte, im Portfolio-Demo (andere Momentaufnahme) nicht; nur XLE deckungsgleich. Ansatz: beim echten Endpunkt sind beide aus derselben Quelle konsistent; für die Demo optional die Inbox-Konflikte 1:1 aus dem Portfolio-Demo spiegeln.

### Frontend-Vollausbau — Slice 5 (Backtester, Branch `feat/frontend-slice5-backtester`)

- [x] **Frontend Slice 5 — Backtester** (Konzept §2.6, Spec §7/§10 US31–US32). Lösung: Backtester über die Tausch-Naht `loadBacktest()` (Demo-Fixture: 12 `BacktestResult[]` quer über Top-Down/Bottom-Up/Judgment × Ticker × underlying × Regime × Horizont). Drei Karten (`BacktestCard`) je Bereich mit Trefferquote, Stichprobengröße n und kumulierter Trefferkurve (`LineCurve` — Wiederverwendung). Vier Filter (`BacktestFilters`): Ticker, Asset-Klasse (underlying), Regime, Zeitfenster (30/60/90 T) — Optionen aus den Roh-Ergebnissen abgeleitet (keine hartkodierten Listen). **UNAVAILABLE ≠ 0** lückenlos durchgezogen: `hitRate([])→rate:null`, `formatHitRate(null)→"n.v."`, leere `equityCurve→[]`, Karte zeigt „n.v."/"Keine Daten" statt „0 %"/Null-Linie. Pure getestete Logik `filterResults`/`hitRate`/`equityCurve`/`formatHitRate`. `/backtester`-Route verdrahtet. TDD grün (alle Tests, inkl. Routing), `npm run build` erfolgreich. Plan: `docs/superpowers/plans/2026-06-23-frontend-slice5-backtester.md`
  > **Abschluss: Mit Slice 5 ist der Frontend-Vollausbau (alle 6 Slices US1–US36) abgeschlossen.**
  > Slice 0 (Fundament/Shell) · Slice 1 (Cockpit-Drilldowns) · Slice 2 (Deep-Dive) · Slice 3 (Portfolio) · Slice 4 (Inbox) · Slice 5 (Backtester) — alle Demo-Naht verdrahtet, TDD grün, `npm run build` erfolgreich.
  > **PR #53 am 2026-06-24 nach master gemergt.** Im Review noch geändert (Commit `91d21a5`): (1) Filter-`regime` von `string` auf die typisierte Union `BacktestRegime` verschärft (löst den in der PR-Beschreibung versprochenen Schreibweisen-Schutz ein; tsc erzwingt es jetzt) · (2) `equityCurve` → **`hitRateCurve`** umbenannt (die Kurve zeigt die Treffer*quote*, keine P/L-Equity — präziser und kollisionsfrei mit der geplanten `equityCurvePnl`) · (3) `hitRateCurve` mit deterministischem Tiebreaker nach `id` bei gleichem Timestamp (+ Test) · (4) Horizont-Cast auf den Alias `BacktestHorizon`. Volle Suite 414 grün, Build grün.

  **Offene Folge-Aufgaben:**
  - [ ] **Echter Backtest-Endpunkt anbinden** — `data/api/backtest.ts` (`fetchBacktest`) statt Demo; die auskommentierte Naht-Zeile in `data/backtest.ts` aktivieren (`isDemo:false`). Backend liefert die historischen Calls je Bereich (Top-Down-Regime-Check, Bottom-Up-Signal-Check, Judgment-Profitabilität) im `BacktestResult[]`-Vertrag.
  - [ ] **P/L-basierte Equity-Kurve** — zusätzliches Feld `pnl` je `BacktestResult` und eine `equityCurvePnl`-Variante (kumulierter P/L in %). Heute bewusst Trefferquote, da kein P/L im Demo-Vertrag (kein Kurs-Zugriff). Erst sinnvoll, wenn der echte Endpunkt P&L je Call liefert.
  - [ ] **US21-Verknüpfung Deep-Dive-Tab** — der Deep-Dive-Tab „Backtest-Kontext" (Slice 2, US21) kann `loadBacktest` + `filterResults({ ticker })` wiederverwenden → Ticker-spezifische Treffsicherheit am Urteil zeigen (Wiederverwendung statt zweiter Quelle). Naht und Filter-Logik sind bereits vorhanden; nur der Tab-Inhalt muss `BacktestCard` einbinden.

### Drilldowns echt — Schritt 1: Buffett-Indikator (Branch `feat/cockpit-serializer-drilldowns`)

- [x] **Buffett-Drilldown end-to-end echt** (US5/US6, 2026-06-25). Ausgangslage: das Frontend zeigte fast nur Demo-Daten; selbst das Cockpit wirkte datenarm. Ursache war **kein** Datenmangel, sondern dass der Serializer die vom Lauf bereits berechneten Buffett-Daten (Weltbank-Länder-Ratios + z-Score + globaler Median, FRED-USA) **nicht durchreichte**. Lösung (TDD durchgängig):
  - **Backend:** `cockpit_to_dict` liefert jetzt `detail.buffett` (Länder mit `iso3/name/ratio_pct/signal/z_score/year/history` + `global_median`, snake_case wie die übrige API). `BuffettCountryPoint` um `name` (Weltbank-Klarname; USA = „United States") + `history` (`(Jahr, Ratio%)`-Serie für den 10-J-Drilldown) erweitert — beides war im Agenten schon vorhanden (Weltbank liefert Name + Serie; die Serie speiste ohnehin den z-Score), wurde nur verworfen. `_fetch_world_bank` reicht jetzt `(Ratio, Jahr, (Jahr,Ratio)-Paare, Name)` durch; z-Score weiter aus den Werten.
  - **Frontend (Tausch-Naht):** neue echte Seite `data/fetchCockpit.ts` (`fetchBuffett`) holt `/api/cockpit` und mappt `detail.buffett` → `BuffettView` (`isDemo:false`, Quell-Zähler, `analyzedIso3` Default „USA", null-Ratio-Länder herausgefiltert); `base` aus `VITE_API_BASE_URL`, `token` aus `localStorage["aaia_token"]` (wie `useAuth`). `loadBuffett` auf `fetchBuffett` umgestellt (Demo-Zeile als Rückfall auskommentiert).
  - **Verifikation:** Backend volle Suite **1134 grün**; Frontend volle Suite **449 grün** (80 Dateien); `npm run build` (tsc+vite) grün. Diff fokussiert (8 geändert + 2 neu).
  - **PR #55 am 2026-06-25 gemergt** (Review Claude: i.O. von Anfang an, keine Befunde — Serializer-Robustheit bei `macro=unavailable` verifiziert, UNAVAILABLE≠0-Filter korrekt, Naht-Disziplin getestet; CI grün).
  - [ ] **Folge: Makro-Inflation echt** — ⚠️ **fachliche Korrektur zuerst nötig:** der Frontend-Vertrag nutzt `InflationRegion = "USA" | "DE" | "CH"`, das Backend (`InflationSnapshot`) liefert aber **Eurozone**, nicht Deutschland. Vor dem Anschluss `DE` → `EZ`/Eurozone korrigieren (Eurozone ≠ Deutschland, AGENTS.md §3) inkl. Demo/UI; dann `detail.macro_inflation` (USA/EZ/CH) durchreichen + `fetchMacro` verdrahten.
  - [ ] **Folge: Rohstoffe / Sentiment / Zinskurve / Sektoren echt** — je eigener PR nach gleichem Muster. Teils **Backend-Anreicherung** nötig: Zinskurve hat nur 2J/10J-Spread (Tenöre 3M/30J + Yield-*Levels* für `CurvePoint[]` fehlen); Rohstoffe haben nur ein **Gruppen**-Signal (Energie/Metalle), der Vertrag will pro-Rohstoff-Signal. Diese Lücken sauberer als UNAVAILABLE/„n.v." zeigen, nicht erfinden.
  - [ ] **Folge: Kursquelle FMP-als-Fallback** (eigener PR) — `yfinance` (inoffizielle Bibliothek) wird auf Render (Rechenzentrums-IP) von Yahoo gedrosselt → leere Cockpit-Ampeln möglich. Robuster: Kurse über die schon integrierte **FMP-API** als Fallback (yfinance None/Fehler → FMP). **Vorher** FMP-Tageslimit vs. Ticker-Zahl pro Lauf prüfen (sonst „yfinance gedrosselt" gegen „FMP-Limit" getauscht) — ggf. Caching.
  - [ ] **Big-Mac:** bewusst weiter **Demo** (mit Nutzer entschieden 2026-06-25) — im Backend existiert kein Big-Mac-Agent (nur Plan `docs/superpowers/plans/2026-06-08-big-mac-index.md`). Später eigener PR.

### Frontend-Detailausbau (intuitiver + Kennzahlen sichtbar) — Initiative ab 2026-06-25

> Nutzer-Auftrag: Frontend **viel detaillierter + intuitiver**, ein neuer Nutzer muss sofort verstehen, wie das Tool funktioniert; die **Kennzahlen/Metriken** der Agenten sichtbar machen (fehlende Daten bleiben Demo); Inspiration Trading-Plattformen (Swissquote). Zerlegt in **drei Teil-Projekte** (mit Nutzer am 2026-06-25 bestätigt: eigene Welcome-Seite, ausgewogenes Karten-Design, Deep-Dive zuerst). Spec: `docs/superpowers/specs/2026-06-25-frontend-onboarding-fundament-design.md`.

- [x] **Teil-Projekt A — Onboarding + Erklär-/Metrik-Fundament** (Branch `feat/frontend-onboarding`, Plan `docs/superpowers/plans/2026-06-25-frontend-onboarding-fundament.md`). Lösung: neue **Willkommen-Seite** (`/willkommen`) erklärt AAIA + jeden der 5 Bereiche („wo finde ich was?") + den Analyse-Ablauf (Top-Down→Bottom-Up→Urteil) + den Demo-Daten-Hinweis; **Erst-Besuch-Routing** (onboarding-bewusster Index-Redirect via `useOnboarding`-Flag in `localStorage`), dauerhaft über **„?" in der Topbar** + **Sidebar-Eintrag**. Dazu der wiederverwendbare **Baukasten** für B/C: `InfoTip` (barrierearmer Fachbegriff-Tooltip), `lib/glossary` (pure Begriff→Erklärung), `SectionCard`, `MetricRow`/`MetricCard` (n.v.-fest, UNAVAILABLE ≠ 0), `welcomeContent` (eine Quelle). TDD durchgängig; volle Frontend-Suite **469 grün** (88 Dateien), `npm run build` grün. **PR #61 am 2026-06-25 gemergt** (Review Claude: Frontend-Suite **lokal nachgefahren** — 469 grün/88 Dateien + `npm run build` grün, da CI nur Backend deckt; Routing/Onboarding + UNAVAILABLE≠0 verifiziert, keine Befunde).
  - [ ] **Teil-Projekt B — Kennzahlen sichtbar machen** (eigene Spec/Plan, **Deep-Dive zuerst**): alle Fundamental-/Bewertungs-/Qualitäts-Metriken pro Titel (KGV/Forward-PE/Shiller-CAPE/PEG/EV-EBITDA/EV-Rev/P-B/P-S/P-FCF/Div-Rendite/WACC/Umsatz-CAGR/Margen/D-E/Altman-Z …) über `MetricRow`/`MetricCard` + `InfoTip`-Erklärungen; danach Cockpit-Drilldowns (Inflation Core/PPI/Realzins, Geldmenge, Zinsen, GDP, Arbeitsmarkt, Kredit, Sektoren). Demo, wo Backend/Serializer noch nicht liefert (Tausch-Naht). Optional eigene **Glossar-Seite** (nutzt `lib/glossary`).
  - [ ] **Teil-Projekt C — UX-Politur (Trading-Plattform-Feel)** (eigene Spec/Plan, querschnitt): Sparklines, dichtere Tabellen-Interaktionen, ggf. globale Suche/Watchlist-Gefühl — aufbauend auf dem Baukasten aus A.

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

- [x] **Konflikt-Backtester (eigener Block)** — bewertet `conflict_resolution` (war der erkannte
  Konflikt richtig + gut aufgelöst?), nicht `short_action`. Anderes Prüf-Subjekt als der
  Short-Backtester. Speist später die Kalibrierung des Konflikt-Agenten.
  **✅ Erledigt — PR #49 am 2026-06-24 gemergt** (Merge-Commit `53ab8e1`). Eigener `ConflictBacktesterAgent` benotet die Verdikte (`HOLD`/`EXIT`/`REVERSE` aus der `conflicts`-Tabelle) gegen die Kursrealität der gehaltenen Position: `r = held_return(direction, adj)` (long→adj, short→−adj); HOLD richtig ⟺ r>0, EXIT ⟺ r<0, REVERSE ⟺ `apply_costs(−r)>0` (strenger). Je Verdikt-Typ aufgeschlüsselt (reuse `aggregate_by_reason`), nur messen. Port-Methode `load_for_backtest`, keine DB-Migration. In `BacktesterChiefAgent` verdrahtet. Umgesetzt subagent-getrieben + Voll-Branch-Review (Opus: „Ready to merge: Yes"), 37 Tests grün. **Im Review (zweiter Blick) nachgebessert:** (1) `graded`-Eintrag trägt `date` → Max-Drawdown chronologisch (Store lädt DESC); (2) fehlender Folgekurs (Delisting) wird als Totalverlust gezählt statt übersprungen (sonst beschönigt ein weggefallenes katastrophales HOLD die HOLD-Trefferquote — Survivorship-Bias; bewusste Asymmetrie zum Short-Backtester, im Spec §5 festgehalten). **Offen (eigene Folge-Blöcke, oben §9):** Befolgungsrate (`verdict` vs. `user_decision`), Kalibrierungs-Rückspeisung.
- [ ] **Konflikt-Befolgungsrate (`verdict` vs. `user_decision`)** — verhaltensbezogenes Maß (folgte
  der Nutzer dem Rat?), getrennt von der Verdikt-Qualität. Liest `conflicts.user_decision`
  (held/closed) gegen `verdict` (HOLD/EXIT/REVERSE) — **keine** Kurse nötig. Eigener kleiner Block;
  baut auf der `load_for_backtest`-Lademethode auf. *(Aus dem Konflikt-Backtester-Faden, 2026-06-24.)*
- [ ] **Short-Konfidenz-Kalibrierung (Rückspeisung)** — die per-Grund-Buckets des Short-Backtesters
  in `compute_confidence` zurückführen (ändert lebendes Verhalten → eigener geprüfter Schritt,
  Disziplin wie Regime-Backtest ②: erst messen, dann anwenden). Hinweis: Die per-Grund-Buckets liegen aktuell nur als Text im `notes`-Feld von `backtester_reports` (kein jsonb) — die Rückspeisung sollte eine `metrics jsonb`-Spalte ergänzen (analog `portfolio_snapshots.metrics`) statt den Notes-String zu parsen.
- [ ] **Long-Backtester auf Short-Tiefe heben (Long-Trefferquoten je Kauf-Grund)** — eigener kleiner Block.
  **Befund (Asymmetrie):** Die Long-Seite *ist* backgetestet (`JudgmentBacktesterAgent`: BUY/SELL gegen Forward-Returns, plus TopDown/BottomUp), aber **flach** — eine *gemeinsame* Gesamt-Trefferquote + Sharpe/Sortino/MaxDD/Profit-Faktor, **ohne** Aufschlüsselung nach Grund und **ohne** die „Trefferquote-vs-Auszahlung"-Warnung. Der Short-Backtester (PR #39) hat diese Tiefe (je Archetyp; Warn-Flag „oft recht, trotzdem Geld verloren"), die Long-Seite nicht. Man sieht also nicht, **welche Kauf-Gründe wirklich Geld bringen** (analog „Distress-Shorts 70 %, Bewertungs-Extrem 45 %").
  **Lösungsansatz (mirror Short-Backtester-Architektur):**
  1. **„Kauf-Grund" für Longs definieren** — anders als die Short-Seite (`short_flags` → `archetypes`) hat die Long-Seite **keine** Archetyp-Registry. Erst festlegen, was ein Kauf-Grund ist: entweder die vorhandenen Treiber (`dominant_signal`/`alignment`/Regime) als Gruppierung nehmen, **oder** einen Long-Archetyp-Katalog bauen (analog `short_flags`: z. B. Unterbewertung, Quality+Moat, Aufwärts-Momentum, Earnings-Beschleunigung). **Eigene kurze Brainstorm-/Design-Entscheidung** — nicht raten.
  2. **Grund + Long-Konfidenz persistieren** — analog `short_meta jsonb`. **Vorher prüfen**, was `analysis_memory` schon trägt (`recommendation`, `confidence`, `dominant_signal`, `alignment`, `indicators_snapshot`) — evtl. reicht das vorhandene Material und es braucht keine neue Spalte.
  3. **Aggregation wiederverwenden** — `aggregate_by_reason`/`payoff_warning` (`core/utils/short_backtest.py`). **Achtung Rule of Three:** Das wäre der **dritte** Nutzer (Short + Konflikt + Long) → jetzt fällig, die Funktionen in ein **gemeinsames, schlüssel-neutrales Aggregat-Modul** zu extrahieren (eigener kleiner Refactor-PR davor oder im selben PR). *(Verweis: die DRY-Entscheidung im Konflikt-Backtester-Spec §6 stellt genau das bis zum dritten Nutzer zurück.)*
  4. **Long-Benotung auf dieselbe Form** — markt-bereinigter Forward-Return, je Kauf-Grund Trefferquote + CI, mittlere Auszahlung, Profit-Faktor, Max-Drawdown, Warn-Flag. Kein Borrow (Long). BUY = Einstieg (stieg netto?), SELL = Ausstieg (kontrafaktisch, analog COVER).
  **Prio: niedrig–mittel** — **kein** Korrektheits-Defekt (die Long-Seite *wird* bewertet), sondern eine Tiefen-/Granularitäts-Verbesserung, damit Long und Short symmetrisch auswertbar sind. *(Idee aus dem Konflikt-Backtester-Faden, 2026-06-24.)*
- [ ] **Backtester-Provider-Helfer nach `core/utils` extrahieren (Rule of Three erreicht)** — `_default_price_on_horizon`/`_default_benchmark_return` sind **private** Helfer in `agents/backtester/bottom_up_backtester_agent.py`, werden aber inzwischen von **drei** Backtestern importiert (judgment, short, **conflict**). Privates Cross-Agent-Coupling: refactort jemand `bottom_up_backtester`, brechen die anderen still. **Lösung:** in ein öffentliches Modul ziehen (z. B. `core/utils/backtest_providers.py` oder `agents/backtester/_providers.py`), alle drei (+ `BacktesterChiefAgent`) umstellen. **Zusammen mit** der `aggregate_by_reason`/`payoff_warning`-Extraktion (oben beim Long-Backtester-Block genannt) in **einem** Aufräum-PR — beide werden beim dritten Nutzer fällig. **Prio: niedrig** (Hygiene, kein Defekt). *(Befund Final-Review Konflikt-Backtester, 2026-06-24.)*
- [ ] **`datetime.utcnow()`-Deprecation aufräumen** — `core/domain/events.py:10` (`default_factory=datetime.utcnow`) u. a. lösen eine `DeprecationWarning` aus (in Python entfernt in künftiger Version). Auf `datetime.now(timezone.utc)` umstellen, damit die Testausgabe sauber bleibt. **Prio: niedrig.** *(Befund Final-Review Konflikt-Backtester, 2026-06-24.)*

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
- [x] **Konflikt-UX (Inbox + Entscheidungs-Protokoll)** — Folge des Konflikt-Agenten; **jetzt baubar** (Block #3 / PR #7 erledigt).
  **⚠️ VOR dem Bau `docs/short.md` §19 lesen — dort liegt der vollständige Design-Kontext + alle Brainstorm-Entscheidungen.** Das Logbuch hält hier nur den **Status**; das **Design lebt im Short-Hub** (`short.md`). Kurzfassung: Tool handelt nie selbst (zeigt Konflikt + fragt „halten/schließen?" + protokolliert nur die Antwort); persistente **Inbox** (offen → erledigt); Auslöser **on-demand + proaktiv**. Verdikt-Auswertung/Kalibrierung = Block #4.
  **PR-Protokoll (§5): PR #28 am 2026-06-22 gemergt** (Konflikt-UX: `ConflictItem`, `ConflictStorePort` + `SupabaseConflictStore`, `conflict_inbox.record_conflict` mit Dedupe + Reopen-nur-bei-schärferem-Verdikt, on-demand im `judgment_orchestrator` + proaktiver `background_runner`-Scan, CLI `conflicts`/`resolve`, `conflicts`-Tabelle). **Deploy nötig:** `CREATE TABLE conflicts`. Im Review (User) ein 🔴-Befund behoben: der proaktive Scan-Orchestrator trug den `conflict_store` → `run()` nahm den Konflikt schon als `source="on_demand"` auf, der proaktive `record_conflict` lief in den Dedupe → `source="proactive"` erreichte die DB **nie**; Fix via `_build_scan_orchestrator(conflict_store=None)` + Regressions-Test. *(Unterpunkte skip_prose + Markt-je-Position bleiben unten offen.)*
  **PR #31 am 2026-06-22 gemergt** (CI-Härtung — war nötig, um #28s hängende/gelbe CI zu entblocken: `tests/conftest.py` blockt `requests`/`yfinance` global → 5 Agenten mit hardcoded I/O fallen auf Defaults zurück, Suite offline-sicher; `pytest --timeout` + `timeout-minutes`; flakiger WS-Test geskippt. Folgeaufgaben dazu oben). *(Beide Vermerke: bewusste Direkt-auf-`master`-Ausnahme.)*
  - [ ] **Konflikt-Scan: skip_prose-Optimierung (LLM nur bei echtem Konflikt)** — der proaktive Depot-Scan im `background_runner` nutzt heute **Voll-Reuse** von `JudgmentOrchestrator.run` (eine vollständige `judge`-Analyse inkl. **LLM-Prosa pro Position**). Optional ein `skip_prose`-Flag durch den Judgment-Pfad fädeln, sodass der LLM (Konflikt-Urteil/These) nur bei **echtem** Konflikt läuft. **Prio: niedrig** — bei kleinem Depot sind die Kosten trivial; die getestete Scan-Logik (`agents/conflict/portfolio_conflict_scan.py`) bleibt davon unberührt.
  - [ ] **Konflikt-Scan: Markt je Position statt `market="USA"`-Default** (`background_runner.py:_SCAN_MARKET`) — der proaktive Scan nutzt für **alle** Positionen US-Top-Down-Kontext; Nicht-US-Titel bekommen so den falschen Makro-Kontext. **Lösung:** Markt aus der `Position` ableiten (Currency/Land → USA/CH/Eurozone) und an `JudgmentOrchestrator.run(market=…)` geben. **Prio: niedrig** (bekannte Vereinfachung, im Design als Default akzeptiert). *(Review PR #28.)*
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
- [x] **Block #4 — Short-Backtest (Short-Backtester-Teil)** — eigener `ShortBacktesterAgent`, der `short_action` getrennt benotet. **✅ Erledigt, PR #39 — siehe Vermerk unten.** *(Konflikt-Backtester + Short-Konfidenz-Kalibrierung bleiben als eigene Folge-Blöcke offen, siehe oben.)*

    > **PR-Protokoll (§5): Block #4 Short-Backtester → PR #39 am 2026-06-23 gemergt** (Merge-Commit `2335d17`). Eigener `ShortBacktesterAgent` (Geschwister zum Judgment-Backtester) benotet die echten Short-Entscheidungen (`short_action ∈ {SHORT, SHORT+, COVER}`) **getrennt**: reine Mathematik in `core/utils/short_backtest.py` (gestaffelte Leih-Kosten 1 %/8 %/manuell anteilig, Einstieg-/Ausstieg-Benotung, Aufschlüsselung nach Grund mit Trefferquote+CI/Profit-Faktor/MaxDrawdown + Warn-Flag „oft recht, trotzdem Geld verloren"), neue Persistenz-Spalte `short_meta jsonb` (Grund/Konfidenz/Borrow-Flag). Nur messen, kein Zurückschreiben. Fachlicher Kernpunkt: fehlende Folgekurse werden **explizit übersprungen** (nicht `forward_return`s `-1.0`), weil eine Delistung für einen Short ein **+100 %-Gewinn** wäre — die Long-Konvention hätte den größten Short-Gewinn still als Katastrophen-Verlust verbucht. **⚠️ Deploy-Schritt:** vor Deploy einmalig `ALTER TABLE analysis_memory ADD COLUMN short_meta jsonb DEFAULT '{}'::jsonb;` auf Supabase ausführen (sonst schlägt **jeder** `save_analysis`-INSERT fehl, nicht nur der Backtester). **Review (zweiter Blick) — zwei Punkte im Branch nachgebessert (TDD):** **(1)** der `ShortBacktesterAgent` war gebaut, aber **nirgends aufgerufen** (lief nur in Tests) → jetzt in `BacktesterChiefAgent` mit denselben injizierten Providern verdrahtet und im `gather` mitgestartet (Commit `35230f3`); **(2)** Max-Drawdown rechnet jetzt **explizit chronologisch** statt in Einlese-Reihenfolge — Zahl ändert sich nicht (max_drawdown ist umkehr-invariant, über 200k Folgen verifiziert), aber die Korrektheit hängt nicht mehr an dieser nicht-offensichtlichen Invarianz (Commit `1f53e5e`). Specs/Plan: `docs/superpowers/{specs,plans}/2026-06-23-short-backtester*`. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*
- [x] **Track B — `ShortThesisAgent` (LLM)** — Fließtext-These + XAI auf der Engine. **Erledigt, PR #23 — siehe Vermerk unten.**

    > **PR-Protokoll (§5): Track B `ShortThesisAgent` → PR #23 am 2026-06-22 gemergt** (Merge-Commit `ad89290`). LLM-Agent (Muster `ConflictAgent`) erzeugt aus dem deterministischen `ShortAssessment` zwei Texte — `short_thesis` (angezeigt, analog `judgment`) + `short_xai` (persistiert in neuer Spalte `analysis_memory.short_xai`, analog `xai_explanation`); zwei sequenzielle LLM-Calls (These → XAI nutzt die These), vollständig defensiv (`("", "")`), vom `JudgmentOrchestrator` **immer** (null-sicher) aufgerufen. Migration `ALTER TABLE analysis_memory ADD COLUMN short_xai text;` vorab auf Supabase ausgeführt. **Review (zweiter Blick) — drei Punkte im Branch nachgebessert (TDD, Gesamtsuite 808 grün; Commit `4591916`):** **(1)** zwei fehlende **Fehlerpfad-Tests** im Orchestrator ergänzt (`short_assessment=None` → Agent nicht aufgerufen; Agent wirft → Felder leer, kein Crash — AGENTS.md §4); **(2)** `_assessment_block` weist fehlende Größe/Stop als `n/v` statt irreführendem `None%` im LLM-Prompt aus; **(3)** `bus.publish` **separat umhüllt** → ein Bus-Fehler verwirft die bereits berechneten LLM-Texte nicht mehr. Specs/Plan: `docs/superpowers/{specs,plans}/2026-06-22-short-thesis-agent*`. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash, kann also nicht mehr in den bereits gemergten PR.)*
- [x] **Equity-Momentum-Agent (long + short)** — `MomentumSnapshot` (analog Index), aktiviert die dormanten Momentum-Flags. **✅ Erledigt, PR #22 am 2026-06-22 gemergt** (Merge-Commit `8a71ace`). Code-Beleg gegen `master` (2026-06-23): `agents/stock_deep_dive/equity/momentum_agent.py` (RSI-14/MA50/MA200/Golden-Cross/relative Stärke, defensiv + `default()`); das vormals dormante `momentum_breakdown`-Flag feuert jetzt aus `bu.momentum` (`core/domain/short_flags.py:64`) → speist Short; `MomentumSnapshot.signal` speist Long. Die zwei Folge-Aufgaben dazu bleiben offen: Index-RS region-/mutter-bewusst (heute fix `URTH`) + `_detect_crossover`/`_signal` des Index-Agenten auf `core/utils/momentum.py` dedupen.
- [ ] **Asset-Klassen-Shorts** — Rohstoff (Roll-Yield/Carry, Cost-Curve-Boden), Anleihe (Carry/Duration/Credit-Asymmetrie), Edelmetall. Je eigener Block.
- [ ] **Futures-Einbau via Taxonomie-Redesign (`underlying` × `wrapper`)** — Scope/Brainstorming **am 2026-06-21 abgeschlossen**; Design + Impact + Frontend-Konzept geschrieben. Statt einer „6. Klasse" ersetzen zwei Felder die `asset_class`: `underlying` (equity/equity_index/bond/commodity/precious_metal) wählt die Engine, `wrapper` (single/fund/future/physical_etc) schaltet eine Schicht zu. **Futures = `wrapper`, keine eigene Klasse.** Umfang Stufe 1: Rohstoff-/Edelmetall-Futures + physische Metall-ETCs.
  Specs: `docs/superpowers/specs/2026-06-21-anlageklassen-taxonomie-design.md` (Design + §13-Entscheidungen) · `…-impact.md` · `…-frontend-konzept.md`.
  **PR-Protokoll (§5):** Spec-PR **PR #18 am 2026-06-21 gemergt** (Merge-Commit `a32433b`). Review (zweiter Blick): alle Code-Verweise gegen `master` verifiziert (stimmen), Finanz-Formeln nachgerechnet (korrekt). Im Review nachgebessert (Commit `9793a16`): (1) Frontend §1 an die §6-Entscheidungen angeglichen (React/WebSocket-live/automatischer Big-Mac statt der veralteten Svelte/Polling/manuell-Empfehlung); (2) „Mispricing"-Reste in Design §6.4/§11 auf die §13.4-Entscheidung (implizite Convenience-Yield vs. eigene Historie) korrigiert; (3) §11 klargestellt, dass die Phase-1-Regression nur für `wrapper ∈ {single, fund}` verhaltens-erhaltend ist und der `etf`-Reklassifizierungstest das **neue** Index-Ergebnis prüft. **Eintrag bleibt offen** — nur das Design ist gemergt, die 3 Umsetzungs-Phasen stehen noch aus.
  **Reihenfolge: erst Equity-Short fertig, dann Phase 1.** Umsetzung in 3 Phasen (je Spec→Plan→PR, TDD):
  - [x] **Phase 1 — Taxonomie-Fundament** (verhaltens-erhaltend): `Underlying`/`Wrapper`-Enums; `BottomUpResult`, Orchestrator-Dispatch (`match underlying`), `recommendation` (`_short_type`-§8.4-Matrix), `short_assessment`-Weiche, `top_down_context`, `Position`+JSON, CLI; `index`→`equity_index`; XLE→`equity_index`, Rohstoff-/Minenaktien→`equity`; `etf`-Durchfall behoben. **Plan:** `docs/superpowers/plans/2026-06-23-anlageklassen-taxonomie-phase1.md` (8 Tasks, subagent-getrieben + Reviews). Umsetzung 2026-06-23, **volle Suite 955 grün**; Schluss-Review „ready to merge" (kein Critical/Important). **PR #37 am 2026-06-23 gemergt** (Merge-Commit `a40462a`). Review des Users: 5 Befunde, alle unkritisch/keine Blocker → als Folgeaufgaben festgehalten (CLI-Härtung, Fallback-Tech-Debt, Kosmetik); #4 (Bond-ETF-Abflachung) vor Phase 2 gegengecheckt = safe. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash.)*
    **Nachbereitung / Folgeaufgaben aus dem Review (kein Phase-1-Blocker):**
    - [ ] `_short_type`/`derive_recommendation` haben **keinen Produktions-Aufrufer** (vorbestehend geparkte SHORT-Logik, Foundation-Plan 2026-06-18). Migration trug Signatur+Matrix korrekt nach + testet sie (20 Kombis). Folge: `_short_type` in die Empfehlungs-/Short-Pfad-Logik **zurückverdrahten** ODER `underlying`/`wrapper` in `derive_recommendation` als „reserviert" annotieren.
    - [ ] **Index-ETFs (`equity_index`/`fund`) bleiben aus `net_beta` ausgeschlossen** — Phase 1 hat die alte Mitgliedschaft 1:1 erhalten (kein stiller Finanz-Change). Ob ein Sektor-ETF Aktienmarkt-Beta tragen soll = **fachliche Entscheidung** (mit Track-B-Hedge/F4 abstimmen).
    - [ ] **`underlying`/`wrapper` als eigene DB-Spalten** persistieren (Supabase `analysis_memory`): aktuell wird weiterhin nur der Legacy-`asset_class`-String geschrieben (kein Schema-Change in Phase 1). Vor Umstellung **`ALTER TABLE`**.
    - [ ] **String-Rand-APIs migrieren:** `ShortThesisAgent.run`, `TopDownAnomalyAgent.run`, `judgment_chief.default` sind noch `asset_class: str`-typisiert (werden via `legacy_asset_class` korrekt gespeist) → intern auf `underlying`/`wrapper` umstellen; danach die `getattr(..., "asset_class", "equity")`-Test-Double-Fallbacks (judgment_agent/short_assessment/anomaly_chief/supabase_memory) entfernen (Test-Doubles auf `underlying`/`wrapper` umstellen).
    - [x] **CLI-Härtung (umsetzen, wenn `wrapper` ab Phase 2 zählt):** (a) **Guard gegen Legacy↔neu-Überlappung** — `_LEGACY_VALUES` enthält `commodity`/`precious_metal`, die zugleich gültige neue `underlying`-Werte sind → `bottomup CL commodity single` wird als Legacy abgefangen, `wrapper` auf FUTURE gezwungen, „single" rutscht in `sector`. Heute harmlos (Engine ignoriert `sector`+`wrapper`), ab Phase 2 **stille Fehlklassifizierung**. (b) **CLI-Fehlertext** bei ungültigem `wrapper` (`bottomup AAPL equity_index Technology`) meldet fälschlich „unbekannter underlying-Wert" → getrennte Texte für underlying/wrapper + erlaubte Werte auflisten. *(Review PR #37, 2026-06-23.)* **Lösung (PR #41):** Reiner Helfer `_is_legacy_call(raw_underlying, raw_wrapper)` als **einzige** Legacy-vs-neu-Entscheidung — von `_resolve_taxonomy()` **und** dem Positions-Offset in `main()` genutzt (Sektor-Spalte bleibt synchron, rutscht nicht mehr in die falsche Spalte). `etf`/`index` → immer Legacy; überlappende Werte (`equity`/`bond`/`commodity`/`precious_metal`) → neuer Stil **nur wenn ein gültiger Wrapper folgt** (bewahrt den historischen Default `commodity`/`precious_metal`→FUTURE); `underlying`/`wrapper` getrennt validiert → präzise Fehlertexte mit erlaubten Werten. 11 neue Tests (TDD, zuerst rot). User-Review: von Anfang an i.O., keine Nacharbeit; Vollverifikation im isolierten Worktree (lokal **1025 passed**; die 2 `test_routes_cockpit.py`-Fehler sind PR-unabhängige Test-Isolations-Flakes — isoliert grün, CI Ubuntu **1027 passed, 0 failed**). **PR #41 am 2026-06-23 gemergt** (Merge-Commit `859c1b1`). *(Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme.)*
    - [ ] **Kosmetik:** `SHORT_WARNINGS[DEFENSIVE]`-Text „ETFs oder Indizes" ist enger als die §8.4-Regel (auch Bond-ETF = defensiv); veralteter Kommentar `_EQUITY_CLASSES` @ `portfolio_monitor_agent.py`. **DB-Check vor Phase 2 (Review #4): erledigt — kein Konsument unterscheidet heute `etf`/`fund` von `single` (codeweit keine Branche; Lesepfade geben Rows roh zurück).**
    - [ ] **DRY: erlaubte `underlying`/`wrapper`-Werte aus den Enums ableiten** — die erlaubten Werte stehen als hartkodierter Text in den `ValueError`-Meldungen von `_resolve_taxonomy()` **und** im `__doc__`-Usage-Block von `app/main.py`. Wird ein Enum-Wert (`Underlying`/`Wrapper`) ergänzt, driften diese Texte still. *Lösungsansatz:* die Auflistungen aus `_UNDERLYING_VALUES`/`_WRAPPER_VALUES` (bzw. direkt den Enums) zusammensetzen → eine einzige Quelle. **Prio: niedrig.** *(Befund Review PR #41, 2026-06-24.)*
    - [ ] **Integrationstest für den Positions-Offset in `main()`** — getestet sind `_is_legacy_call` und `_resolve_taxonomy` isoliert; die Verdrahtung in `main()` (Offset `pos[3]` vs. `pos[4]` → landet der Sektor im richtigen Feld?) hat **keinen** Test — genau das war aber das reale Symptom („Sektor rutscht in die falsche Spalte"). *Lösungsansatz:* die Argument-/Offset-Zuordnung aus `main()` in eine reine Funktion extrahieren (z. B. `_parse_positions(pos) -> (underlying, wrapper, sector, bond_type, rate_direction)`) und end-to-end testen (`commodity single Energy` ⇒ `sector="Energy"`). **Prio: mittel** — vor weiterer CLI-Arbeit in Phase 2+. *(Befund Review PR #41, 2026-06-24.)*
    - [ ] **Case-Sensitivity der CLI-Eingaben vereinheitlichen** — `legacy_to_taxonomy()` lowercased intern, aber `_is_legacy_call`/`_resolve_taxonomy` matchen exakt → `EQUITY` (groß geschrieben) wird abgelehnt statt erkannt. **Vorbestehend, kein Regress durch PR #41.** *Lösungsansatz:* entweder konsequent `.lower()` auf die rohen CLI-Strings (nutzerfreundlich, ein Pfad) oder bewusst case-sensitiv im `__doc__` dokumentieren. **Prio: niedrig.** *(Befund Review PR #41, 2026-06-24.)*

    > **PR-Protokoll (§5):** obige drei Folge-Aufgaben via **PR #46 am 2026-06-24 gemergt** (Merge-Commit `a671f98`) ins Logbuch eingetragen — reine Doku-Ergänzung aus dem #41-Review (kein Code, keine CI-Relevanz). *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme.)*
  - [x] **Phase 2 — Wrapper-Schichten + Daten-Ports (Long):** `FuturesCurveProvider` (+ Stub) → Kurve/Roll/Carry/Basis/Hebel/Verfall (Hebel-Deckel ≤ 10 % Nominal); `FundInfoProvider` (+ Stub) → TER + Tracking-Error (braucht Benchmark-Zuordnung); implizite Convenience-Yield aus Preisen (kein „Mispricing"). **Erledigt mit 2a (PR #42) + 2b (PR #43).**

    > **PR-Protokoll (§5): Phase 2a — Futures-Mechanik-Schicht + Nominal-Exposure → PR #42 am 2026-06-23 gemergt** (Merge-Commit `e450ba5`). Reine Terminkurven-Mathematik (`core/utils/futures_curve.py`: `slope_ann`, `roll_yield_long_ann`, `basis`, `cost_of_carry_fair`, implizite `convenience_yield`, ±5 %-Bänder, Roll-Warnung) ohne I/O; Domäne `FuturesCurveSnapshot`/`FuturesAssessment` (+ `unavailable()`); Port `FuturesCurveProvider` + UNAVAILABLE-Stub (echte Quelle = eigene Slice, Stub bewusst **nicht** im Composition Root); Overlay im `BottomUpOrchestrator` nur bei `wrapper=FUTURE` (defensiv → `unavailable()` statt Crash); Nominal-Umstellung der Risiko-Kennzahlen (`Position.contract_multiplier`, Default 1.0; `portfolio_monitor` rechnet Exposure für Futures auf Notional); Hebel→Sizing als konservative `tranche/L`-Vereinfachung. **Review (zweiter Blick) — drei Punkte im Branch nachgebessert (TDD, volle Suite 1050 grün):** **(1) CI-Blocker:** der einzige `@pytest.mark.asyncio`-Test im Repo schlug in der CI fehl (Projekt nutzt bewusst **kein** `pytest-asyncio`, fehlt in der CI) → auf Projektkonvention `asyncio.run` umgestellt, plugin-unabhängig (Commit `946f3b0`); **(2)** `_position_size_pct` rundete bei sehr hohem Hebel die Tranche auf `0.0 %` → Floor **≥ 0,1 %** (nur im Hebel-Fall; ohne Hebel unverändert); **(3)** Begründungstext weist mit Hebel jetzt **Kapitaleinsatz vs. ~L×-höheres Nominal-Exposure** aus, statt das Risiko als „% des Risikobudgets" zu untertreiben (Commit `e48b5d6`). Mathematik (Vorzeichen/Einheiten/Guards) gegengerechnet = korrekt. **Phase 2 bleibt offen** — nur der Futures-Teil (2a) ist drin; der Fund-Teil (`FundInfoProvider`/TER/Tracking-Error, 2b) läuft noch. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash.)*

    > **PR-Protokoll (§5): Phase 2b — Fund-Info-Schicht (TER + Tracking-Error) → PR #43 am 2026-06-24 gemergt** (Merge-Commit `4d9d50c`). Reine Tracking-Error-Mathematik (`core/utils/fund_info.py`: annualisierte Stdev der Renditedifferenz ETF−Benchmark) ohne I/O; Domäne `FundInfo` (ter/tracking_error/available, `unavailable()` + `of()`); Port `FundInfoProvider` + UNAVAILABLE-Stub (echte ETF-Stammdaten-/Benchmark-Quelle = eigene Slice, Stub bewusst **nicht** im Composition Root); Overlay im `BottomUpOrchestrator` bei `wrapper=FUND` (defensiv → `unavailable()` statt Crash). **Review (zweiter Blick) — Befunde + Merge-Konflikt nachgebessert (TDD, volle Suite 1101 grün):** **(1) CI-Blocker:** identisch zu 2a — der einzige `@pytest.mark.asyncio`-Test schlug in der CI fehl → auf Projektkonvention `asyncio.run` umgestellt; **(2) 🔴 Overlay-Reichweite:** das Overlay hing nur am Index-Pfad → Nicht-Index-ETFs (GLD/TLT/USO) bekamen die Schicht nicht; zentral in `run()` gezogen, greift jetzt für **jeden** `wrapper=FUND`; **(3)** `FundInfo.of()` leitet `available` aus der TER ab (Invariante erzwungen statt nur dokumentiert); **(4)** Testlücken geschlossen (Provider wirft/liefert `None` → unavailable; Non-Index-Overlay; Annualisierung mit nicht-default `periods_per_year`). **Merge-Konflikt mit master (nach #42):** rein additiv aufgelöst — Phase 2a (Futures) + 2b (Fund) koexistieren; Dispatch für Edelmetall/Rohstoff von frühem `return` auf Fall-Through umgestellt (Fund-Schicht greift auch dort), Futures-Overlay bleibt pfadlokal. Damit ist **Phase 2 (Long-Wrapper-Schichten) komplett** — echte Datenquellen je Provider sind separate Stub-Replace-Slices. *(Dieser Protokoll-Vermerk: bewusste Direkt-auf-`master`-Ausnahme — braucht den Merge-Commit-Hash.)*

    - [ ] **Phase 2a — Hebel→Sizing verdrahten (Folge aus PR #42-Review):** `derive_recommendation(leverage=…)`/`_position_size_pct` sind durchgereicht, aber **kein** Aufrufer gibt heute `FuturesAssessment.leverage` hinein → der Hebel-Sizing-Pfad ist im Live-Flow ruhend (nur unit-getestet). Anbinden, sobald `FuturesCurveProvider` echt verdrahtet ist (Stub ist bewusst noch nicht im Composition Root). **Ansatz:** im Bottom-Up/Judgment-Pfad die `futures_curve.leverage` an `derive_recommendation` reichen. *(Review PR #42, 2026-06-23.)*

    - [ ] **Phase 2b — `FundInfoProvider` echt verdrahten (Folge aus PR #43):** der UNAVAILABLE-Stub ist bewusst **nicht** im Composition Root → die Fund-Info-Schicht meldet live immer `unavailable`. Echte ETF-Stammdaten-Quelle (TER) + Benchmark-Renditen anbinden (der Tracking-Error braucht die Benchmark-Zuordnung) und den Provider im Bottom-Up-Pfad injizieren. Teil der Stub-Replace-Initiative. *(Review PR #43, 2026-06-24.)*
  - [x] **Phase 3 — Long/Short-Feinschliff:** eigener Short-Zweig für `wrapper=future` (kein Borrow/Squeeze; Roll-Yield für Short; Cost-Curve-Boden als Deckel). **✅ Umgesetzt (Branch `feat/phase3-futures-short`, TDD subagenten-getrieben, volle Suite 1163 grün; **PR #54 am 2026-06-25 gemergt** — Review Claude: Finanzkern verifiziert (Vorzeichen-Symmetrie, Deckel-Richtung am Kostenboden, lückenlose Bänder, Single-Fetch `call_count==1`, Guard-Scope, Sizing/Stop spiegeln Equity-Pfad), keine blockierenden Befunde, CI grün).** **Lösung:** Reine Mathematik `core/utils/futures_short.py` (`roll_yield_short_ann = +slope` — Short profitiert von Contango; `floor_distance_pct`; `carry_state` mit denselben ±5%-Bändern wie `curve_signal`; `assess_futures_short` = Konfidenz aus Bewertungs-Leg (Fallhöhe zum Kostenboden) × Carry, gedeckelt durch den **Cost-Curve-Boden**: nahe/unter Kosten ODER fehlende Floor-Daten → `min(conf,0.49)` → NONE/COVER). Modell `FuturesShortAssessment` (+`unavailable()`), `BottomUpResult.futures_short`. Port `CostFloorProvider` + UNAVAILABLE-Stub (Rohstoff: Grenzkosten; Edelmetall: AISC). Orchestrator: **Single-Fetch** der Terminkurve, von Long- *und* Short-Overlay geteilt; Short-Overlay nur bei `wrapper=future` & Rohstoff/Edelmetall. Andocken im Nicht-Equity-Zweig von `derive_short_assessment` → `_action(current_position, conf, pnl, squeeze)` erzeugt die positions-bewusste `ShortAction` (dockt an Monitor/Memory). Spec/Plan: `docs/superpowers/specs|plans/2026-06-24-phase3-futures-short*`. Quellen bewusst **Stub-First** (nicht im Composition Root) → end-to-end ruht der Short, bis echte Kurven-+Kostendaten landen. **Folge-Aufgaben:**
    - [ ] **Echte Kostenboden-Quelle** für `CostFloorProvider` (Grenzproduktionskosten / AISC) + im Composition Root verdrahten. Bis dahin deckelt der Floor mangels Daten konservativ.
    - [ ] **Regime-Tilt (v2):** underlying-abhängig — Rohstoff-Short Rückenwind in Rezession (Nachfrageausfall), Edelmetall-Short Gegenwind risk-off (Safe-Haven). Heute bewusst neutral.
    - [ ] **Take-Profit am Kostenboden (v2):** den Boden auch als **Ziel** (nicht nur Deckel) nutzen.
    - [ ] **Aktienindex-/Anleihe-Futures-Short:** Roll-Yield-Short ohne Kostenboden — eigener Slice.
    - [ ] **Leverage-bewusste Short-Größe:** die **ganze** `derive_short_assessment`-Bahn ist heute hebel-unaware (`_position_size_pct` ohne `leverage`) — Kapital-vs-Nominal-Sizing für Futures-Shorts nachziehen (gemeinsam mit der Phase-2a-Hebel→Sizing-Aufgabe oben). *(Befund Schluss-Review.)*
    - [ ] **Schwellen kalibrieren** (Bewertungs-Bänder 0.50/0.25/0.10, Carry ±0.10/−0.12) über die Regime-Replay-Initiative ③/④.
    - Hinweis: `FuturesShortAssessment.engine_action` ist die **positions-agnostische Diagnose-Sicht** (für Monitor/Frontend); die positions-bewusste Aktion entsteht in `_action()` — kein Verdrahtungs-Loch.
- [x] **⚠️ Risiko-Kennzahlen auf Nominal umstellen — VOR Track-B-Hedge-Dimensionierung.** Futures-Hebel + physische ETCs verfälschen `net_exposure`/`net_beta` (rechnen heute mit Kapitaleinsatz statt Nominal); ein gehebeltes Buch sähe fälschlich „sicherer" aus. Exposure muss `wrapper`-abhängig auf den **Nominalwert** rechnen. *(Befund Impact-Analyse 2026-06-21; hängt mit der Risiko-Kennzahlen-Verfeinerung F4 oben zusammen.)* **✅ Erledigt mit PR #42 (Phase 2a, 2026-06-23):** `portfolio_monitor._evaluate_positions` rechnet Exposure für `wrapper=FUTURE` auf Notional (`shares·price·contract_multiplier`); `net_exposure`/`gross`/HHI/Vola bilden den Hebel jetzt ab. `net_beta` bewusst **unverändert** (Rohstoff/Edelmetall dort ohnehin ausgeschlossen). Offen bleibt nur die Track-B-Hedge-Dimensionierung selbst (F4).
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
