# Frontend Slice 5 — Backtester — Implementation Plan

**For agentic workers:** Execute the tasks in order. Each task is TDD-first: write the failing test (Rot), implement until green (Grün), then commit. Use **German** for code comments, UI strings, and commit messages (AGENTS.md §0). Run the full test suite (`npm test` = `vitest run` im `frontend/`) before claiming any task done. **Nach jeder Änderung mit Importen zusätzlich `npm run build` laufen lassen** (`tsc -b && vite build`) — Vitest meldet ungenutzte Importe/Variablen **nicht**, der TypeScript-Compiler (`tsc`) schon. Reports gehen nach `.superpowers/sdd/...` (führender Punkt, git-ignoriert) — **niemals** nach `docs/superpowers/sdd/`, und **niemals** Scratch-Dateien committen (kein `git add -A`/`git add -f`; nur die in der File-Structure-Tabelle gelisteten Pfade explizit stagen).

---

## Goal

Baue den **Backtester** (Spec §7 Slice 5, Konzept §2.6, Wireframe §4.10) — die skeptische „hätten die alten Calls Geld gebracht?"-Ansicht. Sie deckt die User-Stories **US31–US32** vollständig ab:

- **US31** — **drei Karten** mit je **Trefferquote** (%), **Stichprobengröße** (n) und einer **Equity-/Trefferkurve** (kumulierte Trefferquote über die Zeit, gerendert mit `LineCurve`):
  - **Top-Down** — war das erkannte **Regime** korrekt? (über die Horizonte 30/60/90 Tage)
  - **Bottom-Up** — war das **dominante Signal** korrekt?
  - **Judgment** — war das Urteil (BUY/SELL/HOLD/SHORT) **profitabel**?
  Jede Karte ist klar als „hätten die alten Calls Geld gebracht" beschriftet.
- **US32** — **Filter**: die Treffsicherheit ist filterbar nach **Ticker**, **Asset-Klasse** (`underlying`), **Regime** und **Zeitfenster** (Horizont 30/60/90 Tage). Die Filter wirken auf die angezeigten Karten und Kurven. Die Filter-/Aggregations-Logik ist eine **pure, getestete Funktion** (Roh-Ergebnisse + Filter → aggregierte Trefferquote/Kurve).

Daten kommen über die **Tausch-Naht** (Spec §2) aus Demo-Fixtures (`loadBacktest`); der Umstieg auf echt bleibt eine Zeile. Kein Backend → die Roh-Ergebnisse sind Demo-Fixtures (`isDemo:true`).

**Fachliche Kernregel (AGENTS.md §3, Spec §1/§5.4):** **UNAVAILABLE ≠ 0.** Eine **leere Stichprobe** (kein Ergebnis nach dem Filter) ist „**keine Daten / n.v.**", **nicht** 0 % Trefferquote. Das durchzieht `hitRate` (liefert `rate:null` bei n=0), die Karten (zeigen „n.v." statt „0 %") und die Kurve (leer statt einer irreführenden Null-Linie).

## Architecture

- **Hexagonal/Naht wie Slice 1–4:** Vertrag (`contract/backtest.ts`) → Naht (`data/backtest.ts` mit `loadBacktest(deps?)`) → Demo-Fixture (`data/demo/backtest.ts`, `isDemo:true`). UI-Komponenten sind dumm und konsumieren über `useView` (Modul-Identität des Loaders → kein Refetch-Loop).
- **Eine Quelle der Wahrheit für die Roh-Ergebnisse:** Das Fixture liefert **`BacktestResult[]`** (ein Ergebnis = ein historischer Call mit `area`, `ticker`, `underlying`, `regime`, `horizon`, `correct`, `timestamp`). Die **drei Karten und alle Filterzahlen werden aus diesen Roh-Ergebnissen berechnet** (`hitRate`/`filterResults`/`equityCurve`) — keine handgesetzten Aggregate, die auseinanderdriften können (gleiches Prinzip wie `demoPortfolio`, das Exposure aus den Positionen rechnet).
- **Reine, getestete Aggregations-/Filter-Logik** in `lib/backtest.ts` (React-entkoppelt, Grenzfälle zuerst):
  - `filterResults(results, filters)` → Teilmenge nach Ticker/`underlying`/Regime/Horizont (jeder Filter optional; `undefined`/`"all"` = kein Filter).
  - `hitRate(results)` → `{ rate: number | null; n: number }`; **`rate:null` bei `n===0`** (UNAVAILABLE ≠ 0), sonst Anteil korrekter Calls in **Prozent** (0..100).
  - `equityCurve(results)` → chronologisch sortierte Kurvenpunkte der **kumulierten Trefferquote** (in %) über die Zeit; leere Menge → leeres Array (keine Null-Linie).
- **Charting:** `LineCurve`/`buildLineOption` (bestehend) für die Equity-/Trefferkurve = Zeitreihe (`x`=Datum, `y`=kumulierte Trefferquote in %). In Tests wird ECharts gemockt (`vi.mock("echarts-for-react", () => ({ default: () => null }))`, wie in `routes.test.tsx`).
- **Filter-Steuerung clientseitig:** Die `BacktesterPage` hält den Filter-State (`useState<BacktestFilters>`); abgeleitete Karten/Kurven entstehen rein durch erneutes Anwenden der puren Funktionen — keine Persistenz, kein Backend.

## Tech Stack

React 19 + TypeScript + Vite + Tailwind v3, react-router-dom v7, Vitest + React Testing Library + `@testing-library/user-event`. Test-Runner: `npm test` (= `vitest run`) im Verzeichnis `frontend/`; Build-Check: `npm run build` (= `tsc -b && vite build`). Kein echter Netz-Call im Test (Fixtures/Fakes). Charting über das bestehende `LineCurve`/`ChartContainer` (ECharts lazy).

## Global Constraints

- **TDD verpflichtend** (AGENTS.md §4): erst der fehlschlagende Test, dann Code. Grenzfälle für die pure Logik **zuerst**: leere Menge → `rate:null`/leere Kurve (n.v., **nicht** 0 %), Filter ohne Treffer, genau **ein** Treffer, alle korrekt (100 %), keiner korrekt (0 % bei n>0 ist legitim — **nur** n=0 ist n.v.).
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL** — leere Stichprobe = „keine Daten / n.v.", niemals als 0 % Trefferquote oder leerer Null-Balken dargestellt.
- **Deutsch** in Kommentaren, UI-Strings, Commit-Messages.
- **Keine magischen Zahlen ohne Begründung** — etablierte Begriffe standardkonform: **Trefferquote** = Anteil korrekter Calls; **Horizont** = Haltedauer in Tagen (30/60/90 T); **Regime** = Marktphase (Boom/Aufschwung/Abschwung/Rezession/Erholung). Jede Schwelle/Definition im Kommentar erklärt.
- Loader stabil an `useView` übergeben (Modul-Identität oder `useCallback`), sonst Refetch-Loop.
- `isDemo` steuert `DemoBadge` automatisch; nicht von Hand ein-/ausblenden.
- Wiederverwenden statt duplizieren: `LineCurve`/`buildLineOption`, `ChartContainer`, `DemoBadge`, `SourceHealth`, `useView`, `formatConfidence` (nur falls 0..1 — Trefferquote ist 0..100, daher **eigener** `formatHitRate`), Typen `Underlying`/`DemoMeta` aus `contract/common.ts`, `SourceHealthMeta` aus `contract/cockpit.ts`.
- **Nach jeder Änderung mit Importen `npm run build`** (tsc fängt ungenutzte Importe/Variablen; Vitest nicht).
- Reports nach `.superpowers/sdd/...` (git-ignoriert); keine Scratch-Datei committen.

---

## File Structure

| Datei | Art | Zweck |
|---|---|---|
| `frontend/src/contract/backtest.ts` | neu | Vertrag: `BacktestArea`, `BacktestHorizon`, `BacktestResult`, `AreaBacktest`, `BacktestView extends DemoMeta, SourceHealthMeta` |
| `frontend/src/lib/backtest.ts` | neu | Pure Logik: `filterResults`, `hitRate` (`rate:null` bei n=0), `equityCurve`, `formatHitRate` |
| `frontend/src/lib/backtest.test.ts` | neu | TDD für `filterResults`/`hitRate`/`equityCurve`/`formatHitRate` (Grenzfälle zuerst) |
| `frontend/src/data/backtest.ts` | neu | Tausch-Naht: `loadBacktest(deps?)` (Demo heute, echte Zeile auskommentiert) |
| `frontend/src/data/demo/backtest.ts` | neu | Demo-Fixture: plausible `BacktestResult[]` quer über Ticker/`underlying`/Regime/Horizonte; `isDemo:true`; Bereichs-Aggregate aus den Roh-Ergebnissen berechnet |
| `frontend/src/data/backtest.test.ts` | neu | Naht-Test: `isDemo:true`, ≥3 Bereiche-Ergebnisse, Aggregate konsistent zu `hitRate`, Filter-Achsen vorhanden |
| `frontend/src/components/backtest/BacktestCard.tsx` | neu | Eine Bereichs-Karte: Titel, Trefferquote (oder „n.v."), n, Equity-/Trefferkurve (`LineCurve`), „hätten die alten Calls Geld gebracht"-Beschriftung |
| `frontend/src/components/backtest/BacktestCard.test.tsx` | neu | Smoke: rendert Titel/Quote/n/Kurve; **n.v.-Pfad** (leere Menge → „n.v.", kein „0 %") |
| `frontend/src/components/backtest/BacktestFilters.tsx` | neu | Filter-Steuerung: Ticker, Asset-Klasse (`underlying`), Regime, Horizont — kontrolliert via Props |
| `frontend/src/components/backtest/BacktestFilters.test.tsx` | neu | Smoke: Auswahl ruft `onChange` mit korrektem Patch; „alle"-Option setzt Filter zurück |
| `frontend/src/pages/BacktesterPage.tsx` | neu | Seite: drei Karten + Filter-State, leitet gefilterte Aggregate aus den Roh-Ergebnissen ab, DemoBadge + SourceHealth |
| `frontend/src/pages/BacktesterPage.test.tsx` | neu | Smoke: drei Karten sichtbar; Filter ändert die angezeigten Zahlen/Kurven; leerer Filter → „n.v." |
| `frontend/src/routes.tsx` | ändern | `/backtester` → `BacktesterPage` statt `PlaceholderPage` |
| `frontend/src/routes.test.tsx` | ändern | `/backtester` rendert `BacktesterPage` (drei Karten-Titel sichtbar) |
| `docs/open_todos.md` | ändern | Logbuch: Slice 5 erledigt + Folge-Aufgaben (echter Backtest-Endpunkt, P/L-Equity statt Trefferquote, US21-Verknüpfung Deep-Dive-Tab) |

---

# DISPATCH A — Naht + pure Logik (Vertrag, Demo-Fixture, `filterResults`/`hitRate`/`equityCurve`)

---

## Task A1 — Vertrag `contract/backtest.ts`

**Files:** `frontend/src/contract/backtest.ts` (neu)

**Interfaces (vollständiger Code):**

```ts
// frontend/src/contract/backtest.ts
// Backtester-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag, BacktestView extends DemoMeta + SourceHealthMeta. Der Backtester beantwortet rein
// rueckblickend "haetten die alten Calls Geld gebracht" (US31) — er fuehrt KEINE Trades aus.
import type { DemoMeta, Underlying } from "./common";
import type { SourceHealthMeta } from "./cockpit";

// Die drei Analyse-Bereiche (Konzept §2.6, Spec §4.10):
// - top_down  : war das erkannte Marktregime korrekt? (ueber die Horizonte)
// - bottom_up : war das dominante Einzeltitel-Signal korrekt?
// - judgment  : war das Urteil (BUY/SELL/HOLD/SHORT) profitabel?
export type BacktestArea = "top_down" | "bottom_up" | "judgment";

// Zeitfenster/Horizont in Handelstagen — Standardhorizonte des Systems (30/60/90 T, US31/US32).
export type BacktestHorizon = 30 | 60 | 90;

// Ein historischer Call = eine Beobachtung im Backtest. `correct` ist die einheitliche
// Erfolgsmetrik je Bereich: Regime korrekt (top_down) / Signal korrekt (bottom_up) /
// Urteil profitabel (judgment). So bleibt die Trefferquote-Mathematik bereichsunabhaengig.
export interface BacktestResult {
  id: string;                 // stabile ID (Bereich+Ticker+Horizont+Datum reicht in der Demo)
  area: BacktestArea;
  ticker: string;             // betroffener Titel/Markt (Filter-Achse, US32)
  underlying: Underlying;     // Asset-Klasse (Filter-Achse, US32)
  regime: string;             // Marktregime zum Zeitpunkt des Calls (Filter-Achse, US32)
  horizon: BacktestHorizon;   // Zeitfenster 30/60/90 T (Filter-Achse, US32)
  correct: boolean;           // war der Call im Nachhinein korrekt/profitabel?
  timestamp: string;          // ISO-Datum des Calls (chronologische Achse fuer die Kurve)
}

// Vorberechnetes Bereichs-Aggregat (fuer die Karten-Vorschau ohne Filter). Wird AUS den
// Roh-Ergebnissen abgeleitet (eine Quelle der Wahrheit) — `hitRatePct:null` => n.v. (n=0).
export interface AreaBacktest {
  area: BacktestArea;
  hitRatePct: number | null;  // Trefferquote in % (0..100); null => leere Stichprobe (UNAVAILABLE != 0)
  sampleSize: number;         // Stichprobengroesse n
}

export interface BacktestView extends DemoMeta, SourceHealthMeta {
  results: BacktestResult[];  // alle Roh-Ergebnisse (Basis fuer Karten + Filter)
  areas: AreaBacktest[];      // vorberechnete Bereichs-Aggregate (ungefiltert), aus results abgeleitet
}
```

**TDD-Steps:**
1. Kein eigener Test (reiner Typ-Vertrag) — die Korrektheit wird durch die Tests in A2–A4 (die diesen Vertrag konsumieren) erzwungen. Lege die Datei an.
2. `npm test` muss weiter grün sein; danach `npm run build` (tsc) — die bestehende Suite kompiliert weiter.
3. Commit:
```
feat(backtest): Vertrag contract/backtest.ts (BacktestResult + BacktestView)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A2 — Pure Logik `lib/backtest.ts` (`filterResults` + `hitRate` + `equityCurve` + `formatHitRate`)

**Files:** `frontend/src/lib/backtest.ts` (neu), `frontend/src/lib/backtest.test.ts` (neu)

**Fachliche Begründung (im Code als Kommentar):**
- **Trefferquote** = Anteil der als `correct:true` markierten Calls an allen Calls der (gefilterten) Stichprobe, in **Prozent** (0..100). Standard-Definition einer Hit-Rate.
- **`rate:null` bei `n===0`** (AGENTS.md §3, Spec §5.4): eine leere Stichprobe ist „**keine Daten**", **nicht** 0 %. 0 % wäre die irreführende Aussage „alle Calls falsch" — das gilt nur bei `n>0`.
- **Equity-/Trefferkurve** = **kumulierte** Trefferquote über die Zeit: nach chronologischer Sortierung wird Punkt für Punkt der laufende Anteil korrekter Calls (in %) gebildet. So ist sichtbar, ob die Treffsicherheit über die Historie stieg/fiel (Konzept §2.6: „hätten die alten Calls Geld gebracht"). Eine leere Menge liefert ein **leeres** Array (keine Null-Linie).
- Filter sind **optional und additiv** (UND-Verknüpfung): ein nicht gesetzter Filter (`undefined`) lässt die Achse offen. Das `area`-Feld ist kein Nutzer-Filter (US32 filtert Ticker/Asset-Klasse/Regime/Horizont), wird aber von der Seite genutzt, um je Karte den Bereich zu wählen — daher als optionaler Teil des Filters mitgeführt.

**Interfaces (vollständiger Code):**

```ts
// frontend/src/lib/backtest.ts
import type { BacktestResult, BacktestArea, BacktestHorizon } from "../contract/backtest";
import type { LinePoint } from "../components/charts/LineCurve";
import type { Underlying } from "../contract/common";

// Filter-Achsen (US32). Jede Achse optional: undefined => kein Filter auf dieser Achse.
// `area` ist kein Nutzer-Filter, sondern die Bereichs-Auswahl der jeweiligen Karte.
export interface BacktestFilters {
  area?: BacktestArea;
  ticker?: string;
  underlying?: Underlying;
  regime?: string;
  horizon?: BacktestHorizon;
}

export interface HitRate {
  rate: number | null; // Trefferquote in % (0..100); null => leere Stichprobe (n=0), n.v. != 0 %
  n: number;           // Stichprobengroesse
}

// Filtert die Roh-Ergebnisse additiv (UND). Nicht gesetzte Achsen lassen die Auswahl offen.
export function filterResults(results: BacktestResult[], filters: BacktestFilters): BacktestResult[] {
  return results.filter((r) => {
    if (filters.area !== undefined && r.area !== filters.area) return false;
    if (filters.ticker !== undefined && r.ticker !== filters.ticker) return false;
    if (filters.underlying !== undefined && r.underlying !== filters.underlying) return false;
    if (filters.regime !== undefined && r.regime !== filters.regime) return false;
    if (filters.horizon !== undefined && r.horizon !== filters.horizon) return false;
    return true;
  });
}

// Trefferquote in % + Stichprobengroesse. WICHTIG (Spec §5.4): leere Stichprobe => rate:null
// ("keine Daten" / n.v.), NICHT 0 %. 0 % gilt nur bei n>0 (alle Calls falsch).
export function hitRate(results: BacktestResult[]): HitRate {
  const n = results.length;
  if (n === 0) return { rate: null, n: 0 };
  const correct = results.filter((r) => r.correct).length;
  return { rate: (correct / n) * 100, n };
}

// Kumulierte Trefferquote ueber die Zeit (chronologisch). Jeder Punkt = laufender Anteil
// korrekter Calls bis dahin, in %. Leere Menge => leeres Array (keine irrefuehrende Null-Linie).
export function equityCurve(results: BacktestResult[]): LinePoint[] {
  const sorted = [...results].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  let correctSoFar = 0;
  return sorted.map((r, i) => {
    if (r.correct) correctSoFar += 1;
    return { x: r.timestamp, y: (correctSoFar / (i + 1)) * 100 };
  });
}

// Trefferquote als Anzeige-String. null => "n.v." (UNAVAILABLE != 0), sonst ganze Prozent.
// Eigener Formatter (NICHT formatConfidence): Trefferquote ist bereits 0..100, nicht 0..1.
export function formatHitRate(rate: number | null): string {
  if (rate === null) return "n.v.";
  return `${Math.round(rate)} %`;
}
```

**Test (vollständiger Code):**

```ts
// frontend/src/lib/backtest.test.ts
import { describe, it, expect } from "vitest";
import { filterResults, hitRate, equityCurve, formatHitRate } from "./backtest";
import type { BacktestResult } from "../contract/backtest";

// Kleines, kontrolliertes Set: 4 Ergebnisse quer ueber Bereich/Ticker/underlying/Regime/Horizont.
const R: BacktestResult[] = [
  { id: "1", area: "top_down",  ticker: "SPY",  underlying: "equity_index",   regime: "Aufschwung", horizon: 30, correct: true,  timestamp: "2026-01-01" },
  { id: "2", area: "top_down",  ticker: "SPY",  underlying: "equity_index",   regime: "Abschwung",  horizon: 60, correct: false, timestamp: "2026-02-01" },
  { id: "3", area: "judgment",  ticker: "AAPL", underlying: "equity",         regime: "Aufschwung", horizon: 90, correct: true,  timestamp: "2026-03-01" },
  { id: "4", area: "bottom_up", ticker: "GC=F", underlying: "precious_metal", regime: "Aufschwung", horizon: 30, correct: true,  timestamp: "2026-04-01" },
];

describe("filterResults (US32 — additiv/UND)", () => {
  it("ohne Filter => unveraendert", () => {
    expect(filterResults(R, {})).toHaveLength(4);
  });
  it("nach Ticker", () => {
    expect(filterResults(R, { ticker: "SPY" })).toHaveLength(2);
  });
  it("nach underlying (Asset-Klasse)", () => {
    expect(filterResults(R, { underlying: "equity" }).map((r) => r.id)).toEqual(["3"]);
  });
  it("nach Regime", () => {
    expect(filterResults(R, { regime: "Aufschwung" })).toHaveLength(3);
  });
  it("nach Horizont (Zeitfenster)", () => {
    expect(filterResults(R, { horizon: 30 })).toHaveLength(2);
  });
  it("kombiniert (UND): Bereich + Regime", () => {
    expect(filterResults(R, { area: "top_down", regime: "Aufschwung" }).map((r) => r.id)).toEqual(["1"]);
  });
  it("Filter ohne Treffer => leere Menge", () => {
    expect(filterResults(R, { ticker: "TSLA" })).toEqual([]);
  });
});

describe("hitRate (US31 — Trefferquote + n; UNAVAILABLE != 0)", () => {
  it("leere Menge => rate:null, n:0 (n.v., NICHT 0 %)", () => {
    expect(hitRate([])).toEqual({ rate: null, n: 0 });
  });
  it("ein einziger korrekter Treffer => 100 %, n:1", () => {
    expect(hitRate([R[0]])).toEqual({ rate: 100, n: 1 });
  });
  it("ein einziger falscher Treffer => 0 % (legitim bei n>0), n:1", () => {
    expect(hitRate([R[1]])).toEqual({ rate: 0, n: 1 });
  });
  it("3 von 4 korrekt => 75 %, n:4", () => {
    const hr = hitRate(R);
    expect(hr.n).toBe(4);
    expect(hr.rate).toBeCloseTo(75, 5);
  });
});

describe("equityCurve (US31 — kumulierte Trefferquote ueber die Zeit)", () => {
  it("leere Menge => leeres Array (keine Null-Linie)", () => {
    expect(equityCurve([])).toEqual([]);
  });
  it("ein Punkt je Ergebnis, chronologisch sortiert", () => {
    const pts = equityCurve(R);
    expect(pts).toHaveLength(4);
    expect(pts.map((p) => p.x)).toEqual(["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]);
  });
  it("kumulierte Quote: 1. korrekt=100 %, nach 2. (1 falsch)=50 %", () => {
    const pts = equityCurve(R);
    expect(pts[0].y).toBeCloseTo(100, 5);
    expect(pts[1].y).toBeCloseTo(50, 5);
  });
  it("sortiert unabhaengig von Eingabereihenfolge", () => {
    const pts = equityCurve([R[3], R[0], R[2], R[1]]);
    expect(pts.map((p) => p.x)).toEqual(["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]);
  });
});

describe("formatHitRate (Anzeige; UNAVAILABLE != 0)", () => {
  it("null => 'n.v.' (keine Daten, NICHT '0 %')", () => {
    expect(formatHitRate(null)).toBe("n.v.");
  });
  it("0 => '0 %' (legitim bei n>0)", () => {
    expect(formatHitRate(0)).toBe("0 %");
  });
  it("75 => '75 %' (gerundet)", () => {
    expect(formatHitRate(75)).toBe("75 %");
    expect(formatHitRate(74.6)).toBe("75 %");
  });
});
```

**TDD-Steps:**
1. Schreibe `backtest.test.ts` (Rot — Modul fehlt).
2. Implementiere `lib/backtest.ts` bis grün.
3. `npm test` — grün; danach `npm run build` (tsc fängt ungenutzte Importe).
4. Commit:
```
feat(backtest): pure Logik filterResults/hitRate/equityCurve/formatHitRate (US31/US32)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A3 — Demo-Fixture `data/demo/backtest.ts` (Aggregate aus Roh-Ergebnissen)

**Files:** `frontend/src/data/demo/backtest.ts` (neu)

**Vorgaben:**
- Definiere ein **plausibles Set von `BacktestResult[]`** (≥ ~12 Einträge), **quer** über:
  - alle drei **Bereiche** (`top_down`/`bottom_up`/`judgment`),
  - mehrere **Ticker** (z. B. `SPY`, `AAPL`, `GC=F`, `TLT`, `XLE`) — konsistent zu den Portfolio-/Deep-Dive-Demos,
  - mehrere **`underlying`** (`equity`, `equity_index`, `precious_metal`, `bond`),
  - mehrere **Regime** (deutsche Phasen-Namen wie `"Aufschwung"`, `"Abschwung"`, `"Rezession"` — konsistent zur Cockpit-Demo, die `"AUFSCHWUNG"` o. ä. nutzt; ein einheitliches Schema wählen und im Kommentar nennen),
  - alle drei **Horizonte** (30/60/90),
  - **gemischte `correct`** (true/false), sodass je Bereich eine **realistisch nicht-perfekte** Trefferquote entsteht (z. B. ~60–75 %), und **aufsteigende `timestamp`** für eine sinnvolle Kurve.
- **Bereichs-Aggregate aus den Roh-Ergebnissen berechnen** (keine handgesetzten Zahlen): für jeden Bereich `hitRate(filterResults(results, { area }))` → `{ area, hitRatePct: hr.rate, sampleSize: hr.n }`. So sind Karten-Vorschau und Roh-Ergebnisse **garantiert konsistent** (gleiches Muster wie `demoPortfolio`).
- **Bewusst auch UNAVAILABLE-Realität abbilden:** mindestens **eine** ausgefallene Quelle in `failed` setzen (z. B. „Historien-Feed (Stub)"), `sourcesActive < sourcesTotal` — der UNAVAILABLE-Pfad wird so real (Spec §1/§5.4). Optional: einen Filter-Schnitt (z. B. ein Ticker × ein Horizont), der **leer** ist, damit der „n.v."-Pfad im UI erreichbar ist — der Code muss damit umgehen, ohne dass es ein Datenfehler ist.
- `isDemo: true`.

**Strukturskizze (vollständiger, direkt verwendbarer Kern — Ergebnisliste exemplarisch zu erweitern):**

```ts
// frontend/src/data/demo/backtest.ts
// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Roh-Ergebnisse quer ueber Bereich x Ticker x underlying x Regime x Horizont; die Bereichs-
// Aggregate werden AUS den Roh-Ergebnissen berechnet (eine Quelle der Wahrheit) -> Karten &
// Filterzahlen driften nicht auseinander (gleiches Prinzip wie demoPortfolio).
// Regime-Namen folgen der Cockpit-Demo (deutsche Phasen, hier gross geschrieben).
import type { BacktestView, BacktestResult, BacktestArea } from "../../contract/backtest";
import { filterResults, hitRate } from "../../lib/backtest";

const RESULTS: BacktestResult[] = [
  // --- TOP-DOWN: war das Regime korrekt? (ueber die Horizonte) ---
  { id: "td-1", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-01-06" },
  { id: "td-2", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "AUFSCHWUNG", horizon: 60, correct: true,  timestamp: "2026-01-20" },
  { id: "td-3", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "ABSCHWUNG",  horizon: 90, correct: false, timestamp: "2026-02-10" },
  { id: "td-4", area: "top_down", ticker: "SPY", underlying: "equity_index", regime: "ABSCHWUNG",  horizon: 30, correct: true,  timestamp: "2026-03-03" },
  // --- BOTTOM-UP: war das dominante Signal korrekt? ---
  { id: "bu-1", area: "bottom_up", ticker: "AAPL", underlying: "equity",         regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-01-13" },
  { id: "bu-2", area: "bottom_up", ticker: "GC=F", underlying: "precious_metal", regime: "AUFSCHWUNG", horizon: 60, correct: false, timestamp: "2026-02-17" },
  { id: "bu-3", area: "bottom_up", ticker: "TLT",  underlying: "bond",           regime: "REZESSION",  horizon: 90, correct: true,  timestamp: "2026-03-24" },
  { id: "bu-4", area: "bottom_up", ticker: "AAPL", underlying: "equity",         regime: "ABSCHWUNG",  horizon: 30, correct: true,  timestamp: "2026-04-07" },
  // --- JUDGMENT: war das Urteil profitabel? ---
  { id: "ju-1", area: "judgment", ticker: "AAPL", underlying: "equity",         regime: "AUFSCHWUNG", horizon: 60, correct: true,  timestamp: "2026-01-27" },
  { id: "ju-2", area: "judgment", ticker: "XLE",  underlying: "equity_index",   regime: "ABSCHWUNG",  horizon: 90, correct: false, timestamp: "2026-02-24" },
  { id: "ju-3", area: "judgment", ticker: "GC=F", underlying: "precious_metal", regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-03-17" },
  { id: "ju-4", area: "judgment", ticker: "TLT",  underlying: "bond",           regime: "REZESSION",  horizon: 60, correct: true,  timestamp: "2026-04-14" },
];

const AREAS: BacktestArea[] = ["top_down", "bottom_up", "judgment"];

export function demoBacktest(): BacktestView {
  // Bereichs-Aggregate AUS den Roh-Ergebnissen ableiten (keine handgesetzten Zahlen).
  const areas = AREAS.map((area) => {
    const hr = hitRate(filterResults(RESULTS, { area }));
    return { area, hitRatePct: hr.rate, sampleSize: hr.n };
  });
  return {
    isDemo: true,
    sourcesActive: 2,
    sourcesTotal: 3,
    // bewusst eine ausgefallene Quelle -> UNAVAILABLE-Pfad sichtbar (Spec §1/§5.4)
    failed: [{ key: "Historien-Feed (Stub)", reason: "Vollstaendige Kurs-Historie noch nicht angebunden" }],
    results: RESULTS,
    areas,
  };
}
```

**TDD-Steps:**
1. Kein dedizierter Test in diesem Task (das Fixture wird in A4 über die Naht getestet). Implementiere das Fixture so, dass es A4 grün macht.
2. `npm run build` (tsc) — keine ungenutzten Importe/Typen.
3. Commit (Fixture allein ist commit-fähig, oder zusammen mit A4):
```
feat(backtest): Demo-Fixture data/demo/backtest.ts (Roh-Ergebnisse + abgeleitete Aggregate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task A4 — Tausch-Naht `data/backtest.ts` + Naht-Test

**Files:** `frontend/src/data/backtest.ts` (neu), `frontend/src/data/backtest.test.ts` (neu)

**Interfaces (vollständiger Code):**

```ts
// frontend/src/data/backtest.ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer den Backtester. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { BacktestView } from "../contract/backtest";
import { demoBacktest } from "./demo/backtest";
import type { ApiDeps } from "./apiDeps";

export async function loadBacktest(_deps?: ApiDeps): Promise<BacktestView> {
  return demoBacktest();
  // return fetchBacktest(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
```

**Test (vollständiger Code):**

```ts
// frontend/src/data/backtest.test.ts
import { describe, it, expect } from "vitest";
import { loadBacktest } from "./backtest";
import { hitRate, filterResults } from "../lib/backtest";

describe("loadBacktest (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit Roh-Ergebnissen", async () => {
    const v = await loadBacktest();
    expect(v.isDemo).toBe(true);
    expect(v.results.length).toBeGreaterThanOrEqual(9);
  });
  it("deckt alle drei Bereiche ab (top_down/bottom_up/judgment)", async () => {
    const v = await loadBacktest();
    for (const area of ["top_down", "bottom_up", "judgment"] as const) {
      expect(v.results.some((r) => r.area === area)).toBe(true);
    }
  });
  it("Bereichs-Aggregate sind konsistent zu hitRate ueber die Roh-Ergebnisse (eine Quelle der Wahrheit)", async () => {
    const v = await loadBacktest();
    for (const a of v.areas) {
      const hr = hitRate(filterResults(v.results, { area: a.area }));
      expect(a.sampleSize).toBe(hr.n);
      expect(a.hitRatePct).toBe(hr.rate);
    }
  });
  it("bietet die Filter-Achsen Ticker/underlying/Regime/Horizont an (US32)", async () => {
    const v = await loadBacktest();
    const tickers = new Set(v.results.map((r) => r.ticker));
    const underlyings = new Set(v.results.map((r) => r.underlying));
    const regimes = new Set(v.results.map((r) => r.regime));
    const horizons = new Set(v.results.map((r) => r.horizon));
    expect(tickers.size).toBeGreaterThanOrEqual(2);
    expect(underlyings.size).toBeGreaterThanOrEqual(2);
    expect(regimes.size).toBeGreaterThanOrEqual(2);
    expect(horizons.size).toBeGreaterThanOrEqual(2);
  });
  it("zeigt mindestens eine ausgefallene Quelle (UNAVAILABLE-Pfad, Spec §5.4)", async () => {
    const v = await loadBacktest();
    expect(v.sourcesActive).toBeLessThan(v.sourcesTotal);
    expect(v.failed.length).toBeGreaterThanOrEqual(1);
  });
});
```

**TDD-Steps:**
1. Schreibe `data/backtest.test.ts` (Rot — Naht + Fixture fehlen, falls A3 noch nicht commit-fähig war).
2. Stelle sicher, dass `data/backtest.ts` (dieser Task) und `data/demo/backtest.ts` (A3) die Tests grün machen.
3. `npm test` — grün; danach `npm run build`.
4. Commit:
```
feat(backtest): Tausch-Naht loadBacktest + Naht-Test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

# DISPATCH B — BacktesterPage + drei Karten + Filter-Steuerung + Kurve + Routing

> Dispatch B baut auf den committeten Artefakten aus Dispatch A auf (Vertrag, Naht, Fixture, pure Logik).

---

## Task B1 — `BacktestCard.tsx` (eine Bereichs-Karte mit Kurve)

**Files:** `frontend/src/components/backtest/BacktestCard.tsx` (neu), `frontend/src/components/backtest/BacktestCard.test.tsx` (neu)

**Exaktes Interface:**

```ts
import type { BacktestResult, BacktestArea } from "../../contract/backtest";

export interface BacktestCardProps {
  area: BacktestArea;          // top_down / bottom_up / judgment
  results: BacktestResult[];   // BEREITS gefilterte Ergebnisse fuer genau diesen Bereich
}
```

**Strukturelle Vorgaben (Wireframe §4.10):**
- Aus `results` per **wiederverwendeter** purer Logik ableiten: `const hr = hitRate(results);` und `const curve = equityCurve(results);` (keine Aggregat-Logik in der Komponente duplizieren).
- **Bereichs-Titel** aus einer kleinen Konstanten-Map (`AREA_LABEL`): `top_down → "Top-Down — Regime korrekt?"`, `bottom_up → "Bottom-Up — dominantes Signal korrekt?"`, `judgment → "Judgment — Urteil profitabel?"`.
- **Untertitel/Beschriftung Pflicht (US31):** ein Satz „Hätten die alten Calls Geld gebracht?" (klar als rückblickende Treffsicherheit beschriftet).
- **Trefferquote** über `formatHitRate(hr.rate)` (zeigt **„n.v."** bei `rate===null` — **kein** „0 %"). Daneben **Stichprobengröße** „n = {hr.n}".
- **Kurve:** wenn `curve.length > 0` → `<LineCurve series={[{ name: "Kumulierte Trefferquote (%)", points: curve }]} height={180} />`. Wenn leer → ein dezenter Hinweis „Keine Daten für diese Auswahl." (n.v.-Pfad, **keine** Null-Linie).
- Karten-Rahmen analog zu den bestehenden Drilldown-/Portfolio-Karten (`rounded-lg border border-slate-200 p-4 dark:border-slate-700`).

**Kern-Test-Assertions:**

```ts
// BacktestCard.test.tsx — Kernfaelle
// ECharts mocken: vi.mock("echarts-for-react", () => ({ default: () => null }))
// 1. rendert Titel + Trefferquote + n bei nicht-leeren Ergebnissen:
//    render(<BacktestCard area="top_down" results={[ correctResult, wrongResult ]} />)
//    expect(screen.getByText(/Top-Down/i)).toBeInTheDocument()
//    expect(screen.getByText("50 %")).toBeInTheDocument()   // 1 von 2 korrekt
//    expect(screen.getByText(/n = 2/)).toBeInTheDocument()
// 2. n.v.-Pfad (leere Ergebnisse) zeigt "n.v." und NICHT "0 %":
//    render(<BacktestCard area="judgment" results={[]} />)
//    expect(screen.getByText("n.v.")).toBeInTheDocument()
//    expect(screen.queryByText("0 %")).toBeNull()
//    expect(screen.getByText(/Keine Daten/i)).toBeInTheDocument()  // kein Chart
// 3. "haetten die alten Calls Geld gebracht"-Beschriftung sichtbar:
//    expect(screen.getByText(/Geld gebracht/i)).toBeInTheDocument()
```

**TDD-Steps:**
1. Schreibe `BacktestCard.test.tsx` (Rot). Baue Test-`BacktestResult`-Objekte inline (ein korrektes, ein falsches) oder importiere `demoBacktest()` und filtere.
2. Implementiere `BacktestCard.tsx` bis grün.
3. `npm test` — grün; danach `npm run build`.
4. Commit:
```
feat(backtest): BacktestCard mit Trefferquote/n/Kurve + n.v.-Pfad (US31)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B2 — `BacktestFilters.tsx` (Filter-Steuerung: Ticker/Asset-Klasse/Regime/Horizont)

**Files:** `frontend/src/components/backtest/BacktestFilters.tsx` (neu), `frontend/src/components/backtest/BacktestFilters.test.tsx` (neu)

**Exaktes Interface:**

```ts
import type { BacktestFilters as Filters } from "../../lib/backtest";

export interface BacktestFiltersProps {
  // Optionen werden aus den Roh-Ergebnissen abgeleitet (von der Seite uebergeben).
  tickers: string[];
  underlyings: string[];      // Underlying-Werte als Strings (Asset-Klasse)
  regimes: string[];
  horizons: number[];         // 30/60/90
  value: Filters;             // aktueller Filter-Zustand (kontrolliert)
  onChange: (patch: Partial<Filters>) => void;  // liefert nur das geaenderte Feld
}
```

**Strukturelle Vorgaben (US32):**
- Vier `<select>`-Steuerungen mit zugänglichem Label (`<label>` + sichtbarer Text oder `aria-label`): **Ticker**, **Asset-Klasse** (`underlying`), **Regime**, **Zeitfenster** (Horizont 30/60/90 T).
- Jede Auswahl hat als erste Option **„Alle"** mit Wert `""`; Auswahl von „Alle" ruft `onChange({ <achse>: undefined })` (Filter zurücksetzen → kein Filter auf dieser Achse). Auswahl eines konkreten Werts ruft `onChange({ <achse>: wert })`.
- Beim Horizont den Wert als `number` (30/60/90) zurückgeben (`Number(e.target.value)` bzw. `undefined` bei „Alle"); Label „30 T / 60 T / 90 T".
- Keine Aggregat-/Filter-Berechnung hier — die Komponente meldet nur Änderungen (die Seite wendet `filterResults` an).

**Kern-Test-Assertions:**

```ts
// BacktestFilters.test.tsx — Kernfaelle (user-event)
// const onChange = vi.fn()
// render(<BacktestFilters tickers={["SPY","AAPL"]} underlyings={["equity","equity_index"]}
//          regimes={["AUFSCHWUNG","ABSCHWUNG"]} horizons={[30,60,90]} value={{}} onChange={onChange} />)
// 1. Ticker waehlen meldet den Patch:
//    await userEvent.selectOptions(screen.getByLabelText(/Ticker/i), "AAPL")
//    expect(onChange).toHaveBeenCalledWith({ ticker: "AAPL" })
// 2. Horizont als number:
//    await userEvent.selectOptions(screen.getByLabelText(/Zeitfenster/i), "60")
//    expect(onChange).toHaveBeenCalledWith({ horizon: 60 })
// 3. "Alle" setzt die Achse zurueck (undefined):
//    await userEvent.selectOptions(screen.getByLabelText(/Asset-Klasse/i), "")
//    expect(onChange).toHaveBeenCalledWith({ underlying: undefined })
```

**TDD-Steps:**
1. Schreibe `BacktestFilters.test.tsx` (Rot).
2. Implementiere `BacktestFilters.tsx` bis grün.
3. `npm test` — grün; danach `npm run build`.
4. Commit:
```
feat(backtest): BacktestFilters (Ticker/Asset-Klasse/Regime/Horizont) (US32)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B3 — `BacktesterPage.tsx` (drei Karten + Filter-State, Aggregate aus den Roh-Ergebnissen)

**Files:** `frontend/src/pages/BacktesterPage.tsx` (neu), `frontend/src/pages/BacktesterPage.test.tsx` (neu)

**Exaktes Interface:**

```ts
import type { BacktestView } from "../contract/backtest";
import { loadBacktest } from "../data/backtest";

export function BacktesterPage({ loader = loadBacktest }: { loader?: () => Promise<BacktestView> }): JSX.Element
```

**Strukturelle Vorgaben:**
- Lädt über `useView(loader)` (Loader-Prop = Modul-Identität als Default → kein Refetch-Loop). Loading/Error-Pfade wie `PortfolioPage` (Lädt …/Fehler).
- Kopf: `<h2>Backtester — Trefferquoten (Track …)</h2>` (z. B. „Backtester — hätten die alten Calls Geld gebracht?") + `<DemoBadge isDemo={data.isDemo} />` + `<SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />`.
- **Filter-Optionen aus den Roh-Ergebnissen ableiten** (eindeutige Werte): `tickers`, `underlyings`, `regimes`, `horizons` via `Set` über `data.results`. So passen die Optionen exakt zu den vorhandenen Daten.
- **Filter-State** via `useState<BacktestFilters>({})` (ohne `area` — `area` wird je Karte gesetzt). `<BacktestFilters … value={filters} onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))} />`.
- **Drei Karten** rendern, je Bereich: `const areaResults = filterResults(data.results, { ...filters, area });` und `<BacktestCard area={area} results={areaResults} />`. So wirkt der Nutzer-Filter (Ticker/underlying/Regime/Horizont) auf **alle drei** Karten gleichzeitig (US32), und die Karte rechnet `hitRate`/`equityCurve` über die gefilterte Bereichs-Teilmenge (US31).
- Leerer Schnitt je Karte → die Karte zeigt „n.v." + „Keine Daten" (kommt aus B1; die Seite muss nichts Zusätzliches tun).

**Kern-Test-Assertions:**

```ts
// BacktesterPage.test.tsx — Kernfaelle
// ECharts mocken: vi.mock("echarts-for-react", () => ({ default: () => null }))
// Helfer: render(<BacktesterPage loader={() => Promise.resolve(demoBacktest())} />)
// 1. Drei Bereichs-Karten sichtbar (US31):
//    await screen.findByText(/Top-Down/i)
//    expect(screen.getByText(/Bottom-Up/i)).toBeInTheDocument()
//    expect(screen.getByText(/Judgment/i)).toBeInTheDocument()
// 2. DemoBadge sichtbar (Fixture isDemo:true):
//    expect(screen.getByText(/Demo-Daten/i)).toBeInTheDocument()
// 3. Filter wirkt: einen Ticker waehlen, der nur in EINEM Bereich vorkommt ->
//    mindestens eine Karte zeigt danach "n.v." (leerer Schnitt). z. B.:
//    await userEvent.selectOptions(screen.getByLabelText(/Ticker/i), "<nur-in-einem-Bereich>")
//    await waitFor(() => expect(screen.getAllByText("n.v.").length).toBeGreaterThanOrEqual(1))
// 4. SourceHealth zeigt die ausgefallene Quelle (x/y aktiv):
//    expect(screen.getByText(/2\s*\/\s*3|Quellen/i)).toBeInTheDocument()  // an SourceHealth-API anpassen
```

> Hinweis für den Implementierer: Für Assertion 3 einen Ticker aus dem Fixture wählen, der in genau einem `area` vorkommt (z. B. ein Ticker, der nur in `top_down`-Ergebnissen auftaucht) — dann werden die beiden anderen Karten „n.v.". Den konkreten Ticker am Fixture aus A3 ausrichten.

**TDD-Steps:**
1. Schreibe `BacktesterPage.test.tsx` (Rot).
2. Implementiere `BacktesterPage.tsx` bis grün.
3. `npm test` — grün; danach `npm run build`.
4. Commit:
```
feat(backtest): BacktesterPage mit 3 Karten + Filter (US31/US32)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B4 — Routing (`/backtester` → BacktesterPage)

**Files:** `frontend/src/routes.tsx` (ändern), `frontend/src/routes.test.tsx` (ändern)

**`routes.tsx`-Änderungen (strukturell):**
- Importiere `BacktesterPage` (`import { BacktesterPage } from "./pages/BacktesterPage";`).
- Ersetze die Platzhalter-Route `<Route path="/backtester" element={<PlaceholderPage title="Backtester" />} />` durch `<Route path="/backtester" element={<BacktesterPage />} />`.
- `PlaceholderPage` bleibt importiert (noch von `/deep-dive` und `/einstellungen` genutzt) — **nicht** entfernen (sonst ungenutzter Import → `tsc`-Fehler beim Build; prüfen mit `npm run build`).

**`routes.test.tsx`-Ergänzung:**

```ts
// Ergaenzung in routes.test.tsx
// /backtester rendert die BacktesterPage (drei Bereichs-Karten-Titel sichtbar):
it("/backtester rendert die BacktesterPage (drei Karten)", async () => {
  renderAt("/backtester");
  await waitFor(() => expect(screen.getByText(/Top-Down/i)).toBeInTheDocument());
  expect(screen.getByText(/Bottom-Up/i)).toBeInTheDocument();
  expect(screen.getByText(/Judgment/i)).toBeInTheDocument();
});
```

**TDD-Steps:**
1. Ergänze `routes.test.tsx` um den Test (Rot — Route zeigt noch den Platzhalter).
2. Verdrahte `routes.tsx` (BacktesterPage-Route statt Platzhalter).
3. `npm test` — grün (inkl. der bestehenden Routing-Tests); danach `npm run build`.
4. Commit:
```
feat(backtest): /backtester-Route -> BacktesterPage (US31/US32)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

## Task B5 — Logbuch `docs/open_todos.md`

**Files:** `docs/open_todos.md` (ändern)

**Vorgaben (AGENTS.md §5):**
- Slice-5-Eintrag **abhaken** mit kurzem **Lösung:**-Hinweis (was/warum/wie): Backtester über die Tausch-Naht (`loadBacktest`), drei Karten (Top-Down/Bottom-Up/Judgment) mit Trefferquote/n/kumulierter Trefferkurve (`LineCurve`), Filter nach Ticker/Asset-Klasse/Regime/Horizont über die pure `filterResults`/`hitRate`/`equityCurve`-Logik; **UNAVAILABLE ≠ 0** durchgezogen (leere Stichprobe → „n.v.", nicht 0 %).
- **Folge-Aufgaben** mit Lösungsansatz ergänzen:
  - **Echter Backtest-Endpunkt** (`fetchBacktest`) → die auskommentierte Naht-Zeile aktivieren; Backend liefert die historischen Calls je Bereich.
  - **P/L-basierte Equity-Kurve** statt kumulierter Trefferquote → zusätzliches Feld `pnl` je `BacktestResult` und eine `equityCurvePnl`-Variante (heute bewusst Trefferquote, da kein P/L im Demo-Vertrag).
  - **US21-Verknüpfung:** Der Deep-Dive „Backtest-Kontext"-Tab (Slice 2) kann denselben `loadBacktest` + `filterResults({ ticker })` nutzen → Ticker-spezifische Treffsicherheit am Urteil zeigen (Wiederverwendung statt zweiter Quelle).
- Diese Logbuch-Änderung läuft **mit im Slice-5-PR** (kein direkter Master-Commit für Code-begleitende Doku — die Master-Ausnahme gilt nur für reine PR-Protokoll-Vermerke).

**TDD-Steps:** Kein Test (Doku). Commit:
```
docs(open_todos): Slice 5 (Backtester) erledigt + Folge-Aufgaben (Endpunkt/P&L/US21)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

---

# Self-Review (vor „fertig")

**US-Abdeckung (jede Story einem Task zugeordnet):**

| Story | Inhalt | Tasks |
|---|---|---|
| **US31** | Drei Karten (Top-Down/Bottom-Up/Judgment) mit Trefferquote, n, Equity-/Trefferkurve; „hätten die alten Calls Geld gebracht" | A1 (Vertrag `BacktestArea`/`AreaBacktest`), A2 (`hitRate`/`equityCurve`), A3 (Fixture über alle 3 Bereiche), A4 (Naht), **B1 (Karte rendert Quote/n/Kurve + n.v.)**, **B3 (drei Karten auf der Seite)** |
| **US32** | Filter nach Ticker/Asset-Klasse/Regime/Zeitfenster (30/60/90 T); Filter wirkt auf Karten/Kurven; pure Filter-Logik getestet | A1 (Filter-Felder im `BacktestResult`), A2 (`filterResults` + Grenzfälle), **B2 (Filter-Steuerung)**, **B3 (Filter wirkt auf alle drei Karten)** |

**Platzhalter-Scan:** Keine absichtlichen Fehlermarker, kein `never`-Trick, keine „entferne diese Zeile". Jeder gezeigte Code (Vertrag, `lib/backtest.ts`, Fixture-Kern, Naht, Tests) ist direkt verwendbar. Der `/backtester`-Platzhalter (`PlaceholderPage`) wird in B4 ersetzt; `PlaceholderPage` bleibt für `/deep-dive`/`/einstellungen` importiert.

**Typ-Konsistenz:** `BacktestResult`/`BacktestView` nutzen `Underlying`/`DemoMeta` aus `contract/common.ts` und `SourceHealthMeta` aus `contract/cockpit.ts`; `LinePoint` stammt aus `components/charts/LineCurve.tsx` (Rückgabetyp von `equityCurve` = `LinePoint[]` → direkt an `LineCurve` übergebbar). `BacktestFilters` (Typ) lebt in `lib/backtest.ts` und wird von Page + Filter-Komponente geteilt. `hitRate` liefert `{ rate: number | null; n }` (nicht 0..1 — daher eigener `formatHitRate`, **nicht** `formatConfidence`).

**Fachliche Korrektheit (AGENTS.md §3):** **Trefferquote** = Anteil korrekter Calls in %; **Horizont** 30/60/90 T = Haltedauer; **Regime** = Marktphase; **kumulierte Trefferquote** als Zeitreihe = etablierte „Equity-/Trefferkurve". **UNAVAILABLE ≠ 0** lückenlos: `hitRate([])→rate:null`, `formatHitRate(null)→"n.v."`, leere `equityCurve`→`[]`, Karte zeigt „n.v."/„Keine Daten" statt „0 %"/Null-Linie. 0 % ist nur bei `n>0` legitim (explizit getestet).

**Naht-Treue:** `loadBacktest(deps?)` spiegelt `loadPortfolio`/`loadInbox` exakt (Demo heute, echte Zeile auskommentiert, `isDemo:true` nur im Fixture). Umstieg = eine Zeile. Bereichs-Aggregate werden aus den Roh-Ergebnissen berechnet (eine Quelle der Wahrheit, wie `demoPortfolio`).

**Charting-Wiederverwendung:** `LineCurve`/`buildLineOption`/`ChartContainer` unverändert wiederverwendet; in Tests ECharts gemockt (`echarts-for-react`).

**Build-Check (Pflicht):** Nach jeder Änderung mit Importen `npm run build` (`tsc -b && vite build`) — tsc fängt ungenutzte Importe/Variablen (Vitest nicht). Vor „fertig": `npm test` (= `vitest run`) **und** `npm run build` grün; Ergebnis nennen. Keine Erfolgsmeldung ohne grünen Lauf (AGENTS.md §4).

**Scratch/Report:** Reports nach `.superpowers/sdd/...` (git-ignoriert). Keine Scratch-Datei committen; nur die in der File-Structure-Tabelle gelisteten Pfade explizit stagen (kein `git add -A`/`-f`).

---

# Dispatch-Gruppierung

- **Dispatch A — Naht + pure Logik** (sequenziell, da A3/A4 auf A1/A2 aufbauen): **A1** Vertrag · **A2** `filterResults`/`hitRate`/`equityCurve`/`formatHitRate` · **A3** Demo-Fixture (Aggregate aus Roh-Ergebnissen) · **A4** Naht + Naht-Test.
- **Dispatch B — UI + Routing** (baut auf committetem A auf): **B1** BacktestCard (Quote/n/Kurve + n.v.) · **B2** BacktestFilters (Ticker/Asset-Klasse/Regime/Horizont) · **B3** BacktesterPage (drei Karten + Filter-State) · **B4** Routing (`/backtester` → BacktesterPage) · **B5** Logbuch.

Reihenfolge: erst Dispatch A vollständig (Vertrag/Naht/Logik stehen + grün), dann Dispatch B. Innerhalb B: B1 → B2 → B3 → B4 → B5.
