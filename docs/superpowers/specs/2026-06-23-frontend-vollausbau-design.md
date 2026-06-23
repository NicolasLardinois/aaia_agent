# Frontend-Vollausbau — Design

> **Status:** Spezifikation / Design-Entwurf · **Datum:** 2026-06-23
> **Scope:** Das **gesamte Frontend** wie im Konzept beschrieben — Cockpit-Drilldowns, Deep-Dive, Portfolio, Inbox, Backtester — als klickbares, vollständiges React-Dashboard. Daten, die das Backend heute noch nicht liefert, kommen aus **austauschbaren Demo-Fixtures**; die bereits live angebundene Cockpit-Übersicht (PR #24/#35) bleibt echt.
> **Erdung:** Setzt das **Frontend-Konzept** `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (User-Stories §2, Informationsarchitektur §3, Wireframes §4, Spezialfälle §5, Entscheidungen §6) und die **erste Scheibe** `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md` um. Baut auf dem bestehenden `frontend/`-Paket (React 19 + TS + Vite + Tailwind v3 + Vitest) auf und erweitert dessen Komponenten-/Anzeige-Logik.
> **Wichtig:** Reines Design-Dokument (*Warum/Wie*). Der **laufende Status** (Roadmap, PR-Protokoll, Folge-Aufgaben) gehört ausschließlich ins Logbuch `docs/open_todos.md` (AGENTS.md §5).

---

## 1. Zusammenfassung & Ziel

Das Konzept (`2026-06-21-frontend-konzept.md`) beschreibt fünf Hauptbereiche und 36 User-Stories. Bisher existiert nur eine Scheibe: die live angebundene **Cockpit-Übersicht** (Regime-Banner + 4 Domänen-Kacheln + Daten-Health + Run-Button, hinter einem Passwort-Gate). Dieses Dokument legt fest, wie das **komplette** Frontend gebaut wird — so, dass **jede** User-Story sichtbar und klickbar abgebildet ist (Traceability-Matrix §10).

**Leitprinzip dieser Ausbaustufe:** Daten, die das Backend noch nicht liefert, werden **nicht** weggelassen und **nicht** pauschal als UNAVAILABLE dargestellt, sondern aus **Demo-Fixtures** gespeist, die fachlich plausibel sind und klar als „Demo-Daten" gekennzeichnet werden. Entscheidend (Nutzer-Vorgabe): **Der Wechsel von Demo- auf echte Daten muss pro Bereich trivial sein** — eine austauschbare Daten-Naht statt verstreuter Fetch-Aufrufe.

**Abgrenzung Demo vs. UNAVAILABLE (wichtig):**
- **Demo-Daten** = „diese Ansicht ist fertig gebaut, aber gespeist aus Beispielwerten, weil der echte Backend-Endpunkt noch fehlt" → sichtbares `DemoBadge`.
- **UNAVAILABLE** = „eine konkrete Quelle ist *innerhalb* eines Ergebnisses ausgefallen/Stub" → gestreift-graues Feld, aus Aggregaten/Konfidenz ausgenommen (Konzept §5.4).
- Beides existiert nebeneinander: Demo-Fixtures enthalten **bewusst auch** UNAVAILABLE-Zustände (z. B. ausgefallene Sub-Agenten), damit dieser UI-Pfad ebenfalls real getestet wird.

---

## 2. Die Tausch-Naht (Datenschicht) — Kern-Architektur

Das Ziel „Demo einfach gegen echt tauschen" wird durch **eine klar definierte Naht pro Bereich** erreicht.

### 2.1 Schichten

```
UI-Komponenten  ──nutzen──▶  Bereichs-Hook  ──ruft──▶  Daten-Quelle (Naht)  ──liefert──▶  Vertrag (TS-Typ)
   (dumm,                      (useDeepDive,             loadDeepDive():            DeepDiveView
    nur Anzeige)                usePortfolio, …)          demo │ real                 (isDemo: boolean)
```

- **`frontend/src/contract/`** — TS-Typen, die exakt die **künftige API-Form** beschreiben (`DeepDiveView`, `PortfolioView`, `InboxView`, `BacktestView`, `BuffettView`, `BigMacView`, `YieldCurveView`, `FuturesView`, …). Demo **und** Echt liefern beide denselben Vertrag → die UI bleibt beim Umstieg unverändert. Jeder Vertrag trägt ein Feld `isDemo: boolean`.
- **`frontend/src/data/`** — pro Bereich **eine** Lade-Funktion (die Naht). Heute gibt sie das Demo-Fixture zurück; die echte Variante ist als auskommentierte/parallele Zeile vorbereitet:

```ts
// frontend/src/data/portfolio.ts
import type { PortfolioView } from "../contract/portfolio";
import { demoPortfolio } from "./demo/portfolio";
import type { ApiDeps } from "./apiDeps";

// HEUTE: Demo-Fixture. SPÄTER: echten Endpunkt aufrufen (Zeile schon vorbereitet).
export async function loadPortfolio(_deps: ApiDeps): Promise<PortfolioView> {
  return demoPortfolio();
  // return fetchPortfolio(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
```

- **`frontend/src/data/demo/`** — die Fixtures. Jede setzt `isDemo: true`.
- **`frontend/src/data/api/`** — (vorbereitet, anfangs leer/Stub) die echten Fetch-Implementierungen; setzen `isDemo: false`.

### 2.2 Automatisches Demo-Etikett

Ein gemeinsames `<DemoBadge view={…} />` liest `view.isDemo`. Weil die echte Quelle `isDemo: false` liefert, **verschwindet das Etikett beim Umstieg automatisch** — kein UI-Edit. Optionaler globaler Override `VITE_DATA_MODE` (`demo` | `real` | `auto`), Default `auto` (jede Naht entscheidet selbst). So bleibt der Umstieg pro Bereich **eine Zeile** (oder ein zentraler Schalter), wie vom Nutzer gefordert.

### 2.3 Was echt bleibt

Die Cockpit-**Übersicht** (`useCockpit` + `getCockpit`/`startRun`/WebSocket) bleibt unverändert echt angebunden. Sie ist die Referenz dafür, wie eine fertige Naht „real" aussieht; die Demo-Nähte sind nach demselben Muster gebaut.

---

## 3. Shell & Navigation (Konzept §3)

- **`react-router-dom`** wird ergänzt (Standard für eine Mehr-Bereichs-SPA).
- **App-Shell** = persistente linke Seitennavigation (Cockpit · Deep-Dive · Portfolio · Inbox · Backtester · Einstellungen) + Topbar mit: **globaler Ticker-/Markt-Suche**, **Inbox-Badge** (Anzahl offener Konflikte), **Daten-Health-Indikator**, **Theme-Umschalter** (hell/dunkel), **Abmelden**.
- Der bestehende `LoginGate`/`useAuth`-Gate umschließt die **ganze** Shell (eine Anmeldung für alles).
- Die heutige `CockpitPage` wird der Unterpunkt **Cockpit → Übersicht**; ihre Live-Anbindung bleibt erhalten.
- **Querverbindungen** (Konzept §3): Ticker-Klick in Portfolio/Inbox/Cockpit → öffnet den Deep-Dive (Route `/deep-dive/:ticker`); Cockpit-Signal im Deep-Dive → zurück ins Drill-down; Inbox-Konflikt → Position im Portfolio + Deep-Dive.

---

## 4. Gemeinsame Komponenten-Bibliothek (Konzept §4-Konventionen, §5)

Neu, wiederverwendbar, jeweils mit **pure-function-Kern** (TDD zuerst):

- **`UnderlyingWrapperBadge`** — Doppel-Etikett `underlying` (🏢 equity · 📈 equity_index · 🏛 bond · 🛢 commodity · 🥇 precious_metal) × `wrapper` (single · fund · future ⏳ · physical_etc). Pure: `underlyingToVisual`, `wrapperToVisual`.
- **`LongShortPanel`** — **zwei gleichwertige Spalten** (links Long BUY/SELL/HOLD/NONE, rechts Short SHORT/COVER/HOLD/NONE), je Urteil-Wort+Farbe, `ConfidenceBar` mit %, Kurzbegründung, XAI-Aufklapp, Schwellen-Flags inline. Pure: `consistencyHint(long, short)` (beide bearish → „starkes bearishes Gesamtbild"; beide NONE/schwach → „kein Edge").
- **`XaiPanel`** (aufklappbar) — Treiber mit Vorzeichen (+/−), Widersprüche, Konfidenz-Begründung, „was es kippen würde" (Konzept §4.6).
- **Schwellen-Badges** — `AutoHoldBadge` (<0.50 → auto-HOLD), `CashBiasBadge` (<0.35). Pure: `confidenceFlags(value)`.
- **`AnomalyReport`** — statistische Ausreißer (|Z|>2.0) + Signalwidersprüche, Schwere none/low/medium/high (Konzept §2.3/`frontend_notes.md`). Pure: `anomalySeverityToVisual`.
- **`DemoBadge`** — „Demo-Daten" (§2.2).
- **`SourceHealth`** — „x/y Quellen aktiv" + aufklappbare Liste ausgefallener Quellen (pro Cockpit-Domäne und pro Deep-Dive; Konzept §5.4). Verallgemeinert den bestehenden `DataHealthIndicator`.
- **Charting-Wrapper über ECharts** (lazy-geladen, framework-agnostische Lib, Konzept §6.1):
  - **`LineCurve`** — Zinskurve (10J/2J/3M/30J) und Futures-Terminkurve (Kontraktmonate).
  - **`BarChart`** — Big-Mac Über-/Unterbewertung.
  - **`EquityCurve`** — Backtester-Equity-/Trefferkurve.
  - **`ChoroplethMap`** — Buffett-Weltkarte (~150 Länder).

**Bestehende Bausteine** (`SignalBadge`, `ConfidenceBar`, `UnavailableField`) werden wiederverwendet, nicht dupliziert.

---

## 5. Charting — ECharts

`echarts` + `echarts-for-react` (oder dünner eigener Wrapper). Eine Bibliothek deckt Linien (Zins-/Terminkurve), Balken (Big-Mac), Equity-Kurven **und** die Choropleth-Weltkarte ab. Charts werden **lazy** importiert (eigener Vite-Chunk), damit das Grund-Bundle schlank bleibt. Farben kommen aus den Signal-Farbkonventionen (grün/rot/grau-blau) und respektieren den Theme-Umschalter.

---

## 6. Fachliche Korrektheit (AGENTS.md §3) — als pure, getestete Funktionen

Diese Anzeige-Logik wird **zuerst** getestet (Grenzfälle explizit) und ist von React entkoppelt:

- **Roll-Yield-Vorzeichen/Richtung:** Contango (Terminpreis > Spot) → Roll-Yield **negativ** (Gegenwind); Backwardation → positiv. Wort **und** Vorzeichen werden benannt, nicht nur Farbe (Konzept §5.1). `rollYieldVisual(value, form)`.
- **Hebel = Nominalwert / Margin** als Faktor (`leverageFactor`).
- **Konfidenz-Schwellen:** <0.50 → auto-HOLD, <0.35 → zusätzlich Cash-Bias (`confidenceFlags`).
- **Zinskurven-Inversion:** Spread-Vorzeichen je Paar (`10J−2J`, `10J−3M`, `30J−10J`), invertiert wenn negativ (`yieldSpreadStatus`).
- **Z-Score-Auffälligkeit:** |Z|≥1.5 = auffällig (⚠) im Buffett-Widget; |Z|>2.0 = Anomalie (`zScoreFlag`).
- **UNAVAILABLE-Ausschluss aus Aggregaten** (bestehende `isUnavailable`-Logik erweitert auf Sub-Agenten/Deep-Dive).

---

## 7. Slice-Decomposition (je ein PR, Abhängigkeits-Reihenfolge)

Jeder Slice ist ein eigener PR auf einem gestapelten Feature-Branch (jeder basiert auf dem vorherigen, da abhängig). Reihenfolge:

| # | Slice | Inhalt | User-Stories |
|---|---|---|---|
| **0** | **Fundament + Shell** | Router, App-Shell (Sidebar+Topbar mit Suche/Inbox-Badge/Health/Theme/Logout), Tausch-Naht (`contract/`+`data/`+`DemoBadge`+`VITE_DATA_MODE`), gemeinsame Bibliothek (UnderlyingWrapperBadge, LongShortPanel, XaiPanel, Schwellen-Badges, AnomalyReport, SourceHealth) + ECharts-Wrapper-Gerüst; Cockpit-Übersicht in die Shell einhängen. | (Infrastruktur für alle) |
| **1** | **Cockpit-Drilldowns** | Makro (Inflation Region+Schwelle), Rohstoffe, Sentiment, Zinskurve (Kurve+3 Spreads+Inversion), Sektoren (Rotation je Regime); Buffett (Tabelle default + Karten-Tab + 10-J-Drilldown + Einschränkungen + Asset-Filter); Big-Mac (Balken + Publikationsdatum). | 2.1: US3,4,5,6,7,8,9 |
| **2** | **Deep-Dive** | Header (underlying×wrapper + Kurs/Markt + „vergleichen"), LongShortPanel + XAI + Schwellen-Flags + AnomalyReport + Cockpit-Rückenwind-Verknüpfung; kontextabhängige Tabs je underlying (Bewertung/Qualität/Signale für equity; Duration/Rating/Spread für bond; Breadth/Momentum/Komposition für index; Supply-Demand/Saisonalität/COT/Cross-Metal für commodity/precious); Futures-Tab (nur wrapper=future: Terminkurve+Roll-Yield+Verfall/Roll+Margin/Hebel); Vergleichsmodus (zwei Wrapper); Sub-Agenten-Health; Backtest-Kontext-Tab. | 2.2: US10–17; 2.3: US18–22; 2.7: US33–36 |
| **3** | **Portfolio (Track B)** | Positionstabelle (Doppel-Etikett, L/S, Größe, Einstand, AAIA-Urteil, Konflikt-Markierung); Exposure brutto/netto + net_beta (aktien-only, datierte Vola) mit Inline-Definitionen; Klumpen-Warnungen (Sektor/underlying/Geographie); Hedge-Vorschläge (beratend, keine Ausführung). | 2.4: US23–27 |
| **4** | **Inbox** | Konflikt-Karten (offen→erledigt), beratendes Verdikt EXIT/HOLD/REVERSE + Begründung, Aktionen markieren erledigt + protokollieren (gefolgt/ignoriert/vertagt), Verlinkung Portfolio/Deep-Dive; Inbox-Badge in der Topbar gespeist. | 2.5: US28–30 |
| **5** | **Backtester** | Drei Karten (Top-Down: Regime korrekt 30/60/90 T · Bottom-Up: dominantes Signal · Judgment: BUY/SELL/HOLD/SHORT profitabel) mit Trefferquote, Stichprobe, Equity-/Trefferkurve; Filter nach Ticker/Asset-Klasse/Regime/Zeitfenster. | 2.6: US31,32 |

**Subagenten:** Jeder Slice wird Task-für-Task von Subagenten umgesetzt (TDD-first, AGENTS.md §4); Reihenfolge sequentiell wegen der Abhängigkeit auf das Fundament.

---

## 8. Tests (TDD verpflichtend, AGENTS.md §4)

- **Pure Anzeige-Logik zuerst** (Vitest): §6-Funktionen mit Grenzfällen (genau auf Schwelle, knapp darüber/darunter, `null`, negative Werte, Contango/Backwardation-Vorzeichen).
- **Komponenten-Smoke-Tests** (React Testing Library): jede neue Komponente rendert ihre Kern-Zustände, inkl. UNAVAILABLE- und Demo-Pfad.
- **Naht-Tests:** Jede `load*`-Funktion liefert den Vertrag inkl. `isDemo`; `DemoBadge` erscheint/verschwindet abhängig vom Flag.
- **Routing-Smoke:** Sidebar-Navigation rendert die Zielseite; Querverlinkungen (Ticker→Deep-Dive) funktionieren.
- Kein echter Netz-Call im Test (Fakes/Fixtures).

---

## 9. Abgrenzung / Nicht-Ziele

- **Keine** Backend-Änderungen außer ggf. CORS (bereits vorhanden). Echte Endpunkte für Deep-Dive/Portfolio/Inbox/Backtester/Buffett/Big-Mac sind **eigene spätere Backend-Aufgaben** (Logbuch) — die Tausch-Naht ist dafür vorbereitet.
- **Keine** Trade-Ausführung (nur beratend — Konzept §2.4/§2.5).
- **Keine** Mehr-Instanz-Skalierung, keine Ergebnis-Persistenz über Neustart (gilt weiter aus Scheibe 1).
- Mobile-Vollausbau ist Nicht-Ziel (Desktop-first, responsiver Tablet-Fallback; Konzept §6.2).

---

## 10. User-Story-Traceability — ALLE 36 Stories (Konzept §2)

> Pflicht-Nachweis: jede Story aus dem Konzept ist genau einem Slice/einer Ansicht zugeordnet. Keine Story entfällt.

### 2.1 Cockpit / Top-Down
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US1 | Marktregime + Konfidenz auf einen Blick | bereits live | Cockpit-Übersicht (Regime-Banner) |
| US2 | 5 Domänen-Kacheln mit zusammengefasstem Signal | bereits live + Slice 0 (Shell) | Cockpit-Übersicht |
| US3 | Inflations-Signal mit Region (USA/EZ-Land/CH) + greifender Schwelle | Slice 1 | Makro-Drilldown |
| US4 | Zinskurve (10J/2J, 10J/3M, 30J/10J) + Inversions-Flag | Slice 1 | Zinskurve-Drilldown (`LineCurve`) |
| US5 | Buffett ~150 Länder durchsuchen/sortieren, Land hervorgehoben, Z-Score, Datenjahr | Slice 1 | Buffett-Widget |
| US6 | Buffett-Einschränkungen am Widget | Slice 1 | Buffett-Widget |
| US7 | Big-Mac Über-/Unterbewertung vs. USD + Publikationsdatum | Slice 1 | Big-Mac-Widget (`BarChart`) |
| US8 | Sektor-Rotation passend zum Regime | Slice 1 | Sektoren-Drilldown |
| US9 | Welche Cockpit-Quellen UNAVAILABLE + Konfidenz-Drückung | bereits live + Slice 1 | Cockpit-Übersicht + Drilldowns (`SourceHealth`) |

### 2.2 Bottom-Up Deep-Dive (underlying × wrapper)
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US10 | Ticker suchen → Header beide Etiketten | Slice 0 (Suche) + Slice 2 | Topbar-Suche + Deep-Dive-Header |
| US11 | Gold-Future vs. physisches ETC vergleichen (Roll-Yield, Hebel) | Slice 2 | Vergleichsmodus |
| US12 | Ölaktie: Öl-Signal aus Cockpit als Rücken-/Gegenwind | Slice 2 | Deep-Dive (Cockpit-Verknüpfung) |
| US13 | Aktie: Bewertung (KGV/EV-EBITDA/DCF), Qualität (Margen/ROIC/Altman-Z), Short-Interest/Insider/Earnings/Moat, Bewertungs-Bandbreite | Slice 2 | Deep-Dive Tabs (equity) |
| US14 | Anleihe: Duration, Credit-Rating, Spread | Slice 2 | Deep-Dive (bond-Variante) |
| US15 | Index: Bewertung, Breadth, Momentum, Sektorkomposition | Slice 2 | Deep-Dive (index-Variante) |
| US16 | Rohstoff/Edelmetall: Supply/Demand, Saisonalität, COT, Cross-Metal-Ratios | Slice 2 | Deep-Dive (commodity/precious-Variante) |
| US17 | Welche Sub-Agenten UNAVAILABLE pro Deep-Dive | Slice 2 | Deep-Dive (`SourceHealth`) |

### 2.3 Long- UND Short-Urteil (XAI)
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US18 | Zwei Urteile nebeneinander (Long + Short) je Konfidenz | Slice 0 (LongShortPanel) + Slice 2 | Deep-Dive |
| US19 | XAI je Urteil (Signale, Widersprüche, warum Konfidenz, was kippt) | Slice 0 (XaiPanel) + Slice 2 | Deep-Dive |
| US20 | Konfidenz <0.50 → auto-HOLD; <0.35 → Cash-Bias | Slice 0 (Badges) + Slice 2 | Deep-Dive |
| US21 | Backtester-Kontext für diesen Ticker | Slice 2 (+ Daten aus Slice 5) | Deep-Dive Backtest-Tab |
| US22 | Anomalie-Report (|Z|>2.0 + Widersprüche, Schwere) am Urteil | Slice 0 (AnomalyReport) + Slice 2 | Deep-Dive |

### 2.4 Portfolio-Manager (Track B)
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US23 | Alle Positionen (long/short) mit beiden Etiketten, Größe, Einstand, AAIA-Urteil | Slice 3 | Portfolio-Tabelle |
| US24 | Netto-/Brutto-Exposure + net_beta (aktien-only, datierte Vola) | Slice 3 | Portfolio-Risiko |
| US25 | Klumpen-Warnungen (Sektor/underlying/Geographie) | Slice 3 | Portfolio-Risiko |
| US26 | Hedge-Vorschläge (Track B, beratend) | Slice 3 | Portfolio-Risiko |
| US27 | Keine Trade-Ausführung, nur Vorschläge | Slice 3 | Portfolio (keine Ausführ-Aktion) |

### 2.5 Konflikt-Inbox
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US28 | Inbox benachrichtigt, wenn Urteil zu gehaltener Position kippt | Slice 4 (+ Badge aus Slice 0) | Inbox + Topbar-Badge |
| US29 | Beratendes Verdikt EXIT/HOLD/REVERSE + Begründung | Slice 4 | Inbox-Karte |
| US30 | Konflikte offen→erledigt abarbeiten (gefolgt/ignoriert/vertagt) + protokollieren | Slice 4 | Inbox (Erledigt-Tab = Audit-Trail) |

### 2.6 Backtester
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US31 | Hätten alte Calls Geld gebracht — getrennt Top-Down/Bottom-Up/Judgment | Slice 5 | Backtester (3 Karten) |
| US32 | Treffsicherheit pro Ticker/Asset-Klasse/Regime filtern | Slice 5 | Backtester-Filter |

### 2.7 Futures-spezifisch
| # | Story (Kurz) | Slice | Ansicht |
|---|---|---|---|
| US33 | Terminkurve (Contango vs. Backwardation) über Kontraktmonate | Slice 2 | Deep-Dive Futures-Tab (`LineCurve`) |
| US34 | Roll-Yield (Vorzeichen) als Zahl | Slice 2 | Futures-Tab |
| US35 | Verfallsdatum + nächster Roll-Termin | Slice 2 | Futures-Tab |
| US36 | Margin + effektiver Hebel der Future-Position | Slice 2 | Futures-Tab |

**Summe: 36/36 Stories abgedeckt.**

---

## 11. Nächste Schritte

1. **Plan je Slice** schreiben (`docs/superpowers/plans/2026-06-23-frontend-slice-*.md`) — TDD-Schritte in Umsetzungsreihenfolge.
2. Umsetzung gestapelt per Slice, je ein PR (AGENTS.md §5, PR-First); Subagenten Task-für-Task.
3. Entscheidungen & Folge-Aufgaben (echte Endpunkte je Bereich) ins Logbuch `docs/open_todos.md`.
4. Render-Ergänzungen am Ende gemeinsam mit dem Nutzer (z. B. Env-Variablen), nachdem der Frontend-Code steht.

---

*Querverweise: `docs/superpowers/specs/2026-06-21-frontend-konzept.md` (Gesamt-Konzept, alle User-Stories, Wireframes), `docs/superpowers/specs/2026-06-22-frontend-cockpit-overview-design.md` (erste Scheibe), `docs/frontend_notes.md` (Buffett-/Big-Mac-Widget, UI-Prinzipien). Status/PR-Protokoll/Folge-Aufgaben: `docs/open_todos.md`.*
