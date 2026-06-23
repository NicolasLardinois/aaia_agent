# Eurozone-Makro (Eurostat-Realwirtschaft) — Daten-Adapter & Verdrahtung — Design

> Slice 1 der Eurozone-Makro-Anbindung innerhalb der Initiative „Stubs → echte Datenquellen".
> Bewusst auf die **Eurostat-Realwirtschaft** beschränkt (Preise + Output). Geldmenge (ECB SDW)
> ist **Slice 2** (eigene Spec/PR); PMI (proprietär) und nominal-BIP-Tweak sind Folge-Tasks.

**Goal:** Die EU-Realwirtschafts-Kennzahlen (HICP, Kern-HICP, PPI, reales BIP-Wachstum, Arbeitslosenquote)
als echte Live-Datenquelle (Eurostat) anbinden, sodass das **EU-Inflationssignal komplett** und das
**EU-BIP-Signal** (über Trend) reale Werte statt `UNAVAILABLE`/NEUTRAL liefern.

**Architektur:** Event-Driven + Hexagonal. Neuer Adapter `adapters/data/eurostat.py` als **Decorator**
über `EcbDataProvider`: die 5 Realwirtschafts-Methoden sind echt (Eurostat), alle übrigen Methoden
(Renditen/Zinsen/Geldmenge/PMI) werden an einen darunterliegenden `EcbDataProvider` (real: `EcbSdwProvider`)
**durchgereicht**. I/O lebt nur im Adapter; das JSON-stat-Parsing ist eine reine, separat getestete Funktion.

**Tech-Stack:** Python, `requests`, pytest.

---

## 1. Befund (Ausgangslage)

- Port `EcbDataProvider` (`core/ports/data_provider.py`) deklariert u. a. `get_cpi`, `get_core_cpi`,
  `get_ppi`, `get_gdp_growth`, `get_unemployment` — heute in `EcbSdwProvider` als Stub → `None`.
- **Konsumenten** (vier Makro-Agenten, keine Änderung nötig):
  - `inflation_agent`: `ecb.get_cpi` **treibt** das EU-Inflationssignal; `get_core_cpi`/`get_ppi` modifizieren.
    Erwartete Einheit: **YoY in Prozent** (z. B. `2.0` = 2,0 %). EU-Bänder: <1 neutral, 1–3 Zielzone (BULLISH),
    3–4 erhöht (BEARISH), >4 BEARISH.
  - `gdp_agent`: `ecb.get_gdp_growth` **treibt** via „BIP über Trend" (EU-Trend 1,2 %); `get_pmi` zusätzlich
    (bleibt vorerst `None` → Signal läuft über Trend allein); `get_unemployment` wird **angezeigt**, treibt
    das Signal nicht (Sahm-Historie fehlt).
- In Produktion (`app/main.py`, `app/server.py`) wird heute `ecb=EcbSdwProvider()` injiziert → EU-Realwirtschaft
  dauerhaft leer.
- **Verifiziert (2026-06-23):** Eurostat liefert mit dem passenden `unit`-Code die **Jahresrate direkt**
  (Beispiel HICP `prc_hicp_manr`, `coicop=CP00`, `unit=RCH_A`, `geo=EA20` → Dez 2025 = `2.0`). YoY muss also
  **nicht** aus Indexreihen gerechnet werden — das entschärft den größten Einheiten-Fehler-Risikofaktor.

## 2. Scope

**In Scope**
1. Neuer Adapter `adapters/data/eurostat.py`: `EurostatEcbProvider(EcbDataProvider)` (Decorator) +
   reine `_parse_jsonstat_latest`-Funktion + geteilter `_fetch_latest`-Helfer.
2. Fünf echte Methoden: `get_cpi`, `get_core_cpi`, `get_ppi`, `get_gdp_growth`, `get_unemployment`.
3. Verdrahtung in den Composition Roots `app/main.py` + `app/server.py`:
   `ecb=EurostatEcbProvider(EcbSdwProvider())`.
4. Tests (TDD).

**Out of Scope (mit Begründung)**
- **Geldmenge (M2/M3) + nominal-BIP-Tweak** → Slice 2 (ECB SDW); berührt Agenten-Logik.
- **PMI** → proprietär (S&P Global), keine kostenlose API; einen Fremdindex mit PMI-Schwellen zu füttern
  wäre fachlich falsch (AGENTS.md §3). Bleibt via Delegation `None`/`UNAVAILABLE`. Folge-Task.
- **`get_balance_sheet_growth`** → von keinem Agenten konsumiert (YAGNI).
- **Keine Agenten-Logik-Änderung** in dieser Slice (reine Datenanbindung).

## 3. Komponenten & Datenfluss

```
app/main.py | app/server.py
        │ injiziert  ecb = EurostatEcbProvider(EcbSdwProvider())
        ▼
EurostatEcbProvider (Decorator, EcbDataProvider)
  ├─ get_cpi/core_cpi/ppi/gdp_growth/unemployment ──► Eurostat (HTTP, JSON-stat)
  └─ alle übrigen Methoden ──────────────────────────► self._base (EcbSdwProvider)
```

- `_parse_jsonstat_latest(data: dict) -> float | None` — **rein**: nimmt aus dem JSON-stat-2.0-`value`-Objekt
  die **jüngste befüllte** Beobachtung = der Wert beim **größten Integer-Key** in `value`. Wichtig: die
  jüngste Zeitperiode ist oft noch nicht veröffentlicht und fehlt dann im `value`-Objekt (steht in
  `positions-with-no-data`) — deshalb NICHT blind den höchsten Zeit-Index nehmen, sondern den größten
  vorhandenen `value`-Key. `None` bei fehlender Struktur, leerem `value` oder nicht-numerisch.
- `_fetch_latest(self, dataset: str, params: dict) -> float | None` — baut die Eurostat-URL
  (`…/statistics/1.0/data/{dataset}?format=JSON&lang=EN&lastTimePeriod=6&…params`), ruft `requests.get`,
  `raise_for_status`, `_parse_jsonstat_latest`. `lastTimePeriod=6` stellt sicher, dass trotz unveröffentlichter
  jüngster Periode mindestens eine befüllte im Fenster liegt. Jeder Fehler → `logging.warning` → `None`.
- Die 5 Methoden sind dünne Konfig-Wrapper (Dataset + Filter).

**Eurostat-Mapping** — alle Codes **gegen echte API-Antworten verifiziert (2026-06-23)**; je eine eingefangene
Antwort dient im Test als Fixture:

| Methode | Dataset | Filter (inkl. `geo`) | Einheit |
|---|---|---|---|
| `get_cpi` | `prc_hicp_manr` | `coicop=CP00`, `unit=RCH_A`, `geo=EA20` | HICP YoY % |
| `get_core_cpi` | `prc_hicp_manr` | `coicop=TOT_X_NRG_FOOD`, `unit=RCH_A`, `geo=EA20` | Kern-HICP YoY % |
| `get_ppi` | `sts_inppd_m` | `indic_bt=PRC_PRR_DOM`, `nace_r2=B-E36`, `s_adj=NSA`, `unit=PCH_SM`, `geo=EA20` | PPI YoY % |
| `get_gdp_growth` | `namq_10_gdp` | `na_item=B1GQ`, `unit=CLV_PCH_SM`, `s_adj=SCA`, `geo=EA20` | reales BIP YoY % |
| `get_unemployment` | `une_rt_m` | `sex=T`, `age=TOTAL`, `unit=PC_ACT`, `s_adj=SA`, **`geo=EA21`** | Arbeitslosenquote % |

> **Stolperstein (verifiziert):** Die Datasets nutzen **unterschiedliche** Euroraum-Codes — HICP/PPI/BIP = `EA20`,
> Arbeitslosigkeit = `EA21` (`EA20` existiert in `une_rt_m` nicht). Pro Methode den korrekten `geo`-Code fest verdrahten.

## 4. Fehler & Beobachtbarkeit (AGENTS.md §3)

- Jede Reihe ist **unabhängig** gekapselt: eine ausgefallene Reihe → `None`; die anderen liefern weiter.
  Der konsumierende Agent gibt für die EU dann sauber NEUTRAL/`UNAVAILABLE` aus — nie ein Crash.
- `logging.warning(...)` bei Netz-/HTTP-Fehler **und** bei `_parse_jsonstat_latest → None` (Strukturbruch),
  damit ein dauerhafter Bruch nicht still bleibt — dieselbe Beobachtbarkeit wie beim CNN-Adapter (PR #34).
- **Plausibilitäts-Caps:** Raten (CPI/Core/PPI/BIP) auf einen weiten Sanity-Bereich prüfen
  (z. B. `-50 … 50` %); Arbeitslosenquote `0 … 100` %. Wert außerhalb → `None` (defensiv gegen
  Fehlparsing/Strukturänderung). Rundung auf 1 Nachkommastelle.

## 5. Tests (TDD, zuerst rot)

`tests/adapters/test_eurostat.py`:
- `_parse_jsonstat_latest` (rein, kein Netz): gültige einzelne Periode; mehrere Perioden → jüngste;
  leeres `value` → `None`; fehlende `dimension.time` → `None`; nicht-numerisch → `None`.
- Je Methode ein Test mit gemocktem `requests.get` (eingefangene JSON-stat-Antwort) → erwarteter Wert;
  ein Fehlerpfad (requests wirft) → `None` (+ WARNING).
- Sanity-Cap: implausibler Wert (z. B. CPI `999`) → `None`.

`tests/test_integration_wiring.py` (oder eigener Adapter-Test):
- **Decorator-Delegation:** `EurostatEcbProvider(fake_base)` reicht nicht-Eurostat-Methoden
  (`get_yield_spreads`, `get_interest_rate`, `get_m3_growth`, `get_pmi`, …) unverändert an `fake_base` durch.

## 6. Logbuch / Doku

- `docs/open_todos.md`: ECB-Eurostat-Einträge (`get_cpi`/`get_core_cpi`/`get_ppi`/`get_gdp_growth`/
  `get_unemployment`) abhaken mit Lösungsvermerk; PMI- und Geldmenge-Folge-Tasks festhalten/präzisieren.
- README: keine Änderung (reine Datenanbindung, kein konzeptionelles Delta).

## 7. Risiken / Annahmen

- Eurostat-Dataset-/Filtercodes für PPI und BIP werden gegen eingefangene echte Antworten gepinnt
  (TDD), damit kein falscher Code still mitläuft.
- Eurostat-API ist offiziell und frei (kein Key, keine `.env`-Änderung); Antwortstruktur JSON-stat 2.0.
- Bei dauerhafter Strukturänderung degradiert der Adapter zu `UNAVAILABLE` (+ WARNING) — kein Crash.
