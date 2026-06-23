# Frontend Slice 2 — Deep-Dive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den Deep-Dive-Bereich pro Anlage bauen — Header mit beiden Etiketten (underlying×wrapper), Long/Short-Urteil + XAI + Schwellen-Flags + Anomalie, kontextabhängige Tabs je `underlying` (equity/bond/index/commodity/precious), Futures-Tab (nur `wrapper=future`), Vergleichsmodus zweier Wrapper, Sub-Agenten-Health, Cockpit-Rückenwind und Backtest-Kontext — alles über die austauschbare Demo-Naht.

**Architecture:** Tausch-Naht wie Slice 1 (`contract/deepdive.ts` → Vertrag, `data/deepdive.ts` → eine Lade-Funktion `loadDeepDive(ticker)`, `data/demo/deepdive.ts` → Fixtures mit `isDemo:true`). Die UI ist dumm und liest nur den Vertrag. Schwellen-/Ableitungs-Logik (Bewertungs-Bandbreite, Altman-Z-Klasse, Duration-Risiko, Hebel/Roll-Yield) wird als **pure, getestete Funktionen** TDD-first gebaut, von React entkoppelt. Tabs sind über eine **Tab-Registry je underlying** gekapselt, sodass pro Basiswert genau die passenden Tabs erscheinen (equity≠bond≠index≠commodity; Futures-Tab nur bei `wrapper=future`).

**Tech Stack:** React 19 + TypeScript + Vite + Tailwind v3 + Vitest + React Testing Library + react-router-dom + ECharts (lazy via `ChartContainer`). Charts werden in Tests gemockt (`vi.mock("echarts-for-react", () => ({ default: () => null }))`).

## Global Constraints

- **Sprache:** Code-Kommentare und UI-Texte durchgehend **Deutsch** (AGENTS.md §0).
- **TDD verpflichtend:** Erst der fehlschlagende Test (Rot), dann minimale Implementierung (Grün), dann aufräumen. Kein Implementierungs-Code ohne vorher geschriebenen Test (AGENTS.md §4). Grenzfälle explizit (genau auf Schwelle, knapp darüber/darunter, `null`, negative Werte).
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL:** Fehlende Sub-Agenten/Felder werden als `null`-Signal über `UnavailableField` / `SignalBadge`(null) gezeigt, nie als 0 oder neutral (Spec §1, Konzept §5.4).
- **Keine magischen Zahlen ohne Begründung:** Jede Schwelle/Formel im Code-Kommentar fachlich begründet, etablierte Konzepte (Altman-Z, EV/EBITDA, DCF, Moat nach Buffett, COT, Contango/Backwardation, Roll-Yield, Duration) standardkonform + im Kommentar verlinkt (AGENTS.md §3).
- **Bestehende Bausteine wiederverwenden, nicht duplizieren:** `UnderlyingWrapperBadge`, `LongShortPanel`/`VerdictLens`, `XaiPanel`/`XaiContent`, `AnomalyReport`/`AnomalyContent`, `ThresholdBadges`, `SourceHealth`/`FailedSource`, `lib/futures.ts` (`rollYieldVisual`/`leverageFactor`/`CurveForm`), `lib/judgment.ts` (`confidenceFlags`/`consistencyHint`/`verdictToVisual`), `lib/anomaly.ts`, `charts/LineCurve` (`buildLineOption`), `contract/common.ts`, `ConfidenceBar`, `SignalBadge`, `UnavailableField`, `DemoBadge`.
- **Tausch-Naht-Muster:** Jeder View `extends DemoMeta & SourceHealthMeta`, `isDemo:true` in Demo-Fixtures; echte Fetch-Zeile in `data/deepdive.ts` auskommentiert vorbereitet (Spec §2).
- **Loader stabil an `useView`:** Page nimmt `loader`-Prop mit Default = Modul-Funktion (Refetch-Loop vermeiden, wie `YieldCurveDrilldown`).
- **Charts in Tests gemockt:** kein echtes ECharts/Canvas im jsdom.
- **Keine Backend-Änderungen.** Echte Endpunkte sind spätere Aufgaben (Logbuch).

---

## File Structure

| Datei | Verantwortung | Dispatch |
|---|---|---|
| `frontend/src/contract/deepdive.ts` | Deep-Dive-Vertrag: `DeepDiveView extends DemoMeta & SourceHealthMeta`, kontextabhängige optionale Blöcke je underlying (`equity?`/`bond?`/`index?`/`commodity?`), `long`/`short` (`VerdictLens`-kompatibel), `anomaly`, `futures?`, `cockpitWind?`, `backtestContext?` | A |
| `frontend/src/lib/valuationRange.ts` | Pure: Bewertungs-Bandbreite-Aggregat (Median der Methoden-lows/highs + Position über/unter/fair, Standard wie `valuation_range_agent`) | A |
| `frontend/src/lib/valuationRange.test.ts` | Tests Grenzfälle (eine/mehrere Methoden, Preis genau auf Band, leer) | A |
| `frontend/src/lib/altman.ts` | Pure: Altman-Z-Klassifikation (safe/grey/distress) je Unternehmenstyp (Original-Z vs. Z'', Financials = n/a) | A |
| `frontend/src/lib/altman.test.ts` | Tests Schwellen 2.99/1.81 + 2.6/1.1 + excluded-Sektor + null | A |
| `frontend/src/lib/duration.ts` | Pure: Duration-Risiko-Einstufung (modified duration → niedrig/mittel/hoch) | A |
| `frontend/src/lib/duration.test.ts` | Tests Schwellen + null | A |
| `frontend/src/lib/deepdiveTabs.ts` | Tab-Registry-Kern: pure `tabsFor(view)` → geordnete Tab-Liste je underlying + Futures-Tab nur bei `wrapper=future` + immer Backtest | A |
| `frontend/src/lib/deepdiveTabs.test.ts` | Tests: equity-Set, bond-Set, index-Set, commodity/precious-Set, Futures-Tab nur bei future, unbekannt → minimal | A |
| `frontend/src/data/deepdive.ts` | Die Naht: `loadDeepDive(ticker, deps?)` (Demo heute, echte Zeile auskommentiert) | A |
| `frontend/src/data/demo/deepdive.ts` | Demo-Fixtures: `AAPL`, `GC=F`, `TLT` (bond), `SPY` (index/fund), `CL=F` (commodity/future), `4GLD` (precious/physical_etc) + `notFound`-Default | A |
| `frontend/src/data/deepdive.test.ts` | Naht-Test: bekannter Ticker → View mit `isDemo`, unbekannt → notFound | A |
| `frontend/src/components/deepdive/DeepDiveHeader.tsx` | Header: `UnderlyingWrapperBadge` + Kurs/Markt + „vergleichen mit"-Einstieg | B |
| `frontend/src/components/deepdive/CockpitWind.tsx` | Cockpit-Signal als Rücken-/Gegenwind + Link ins Drilldown (US12) | B |
| `frontend/src/components/deepdive/tabs/EquityTabs.tsx` | equity-Tab-Inhalte: Bewertung (KGV/EV-EBITDA/DCF + Bandbreite), Qualität (Margen/ROIC/Altman-Z), Signale (Short-Interest/Insider/Earnings/Moat) | B |
| `frontend/src/components/deepdive/tabs/BondTab.tsx` | bond: Duration, Credit-Rating, Spread (US14) | B |
| `frontend/src/components/deepdive/tabs/IndexTab.tsx` | index: Bewertung, Breadth, Momentum, Sektorkomposition (US15) | B |
| `frontend/src/components/deepdive/tabs/CommodityTab.tsx` | commodity/precious: Supply/Demand, Saisonalität, COT bzw. Cross-Metal-Ratios (US16) | B |
| `frontend/src/components/deepdive/tabs/BacktestContextTab.tsx` | Trefferquote/Historie für diesen Ticker (US21, Demo) | B |
| `frontend/src/components/deepdive/tabs/FuturesTab.tsx` | Terminkurve (`LineCurve`) + Roll-Yield + Verfall/Roll + Margin/Hebel (US33–36) | C |
| `frontend/src/components/deepdive/CompareView.tsx` | Vergleichsmodus: zwei Wrapper desselben underlying (Roll-Yield/Hebel/Kosten/Urteil) (US11) | C |
| `frontend/src/pages/DeepDivePage.tsx` | Seite: lädt per `:ticker` über `useView`, rendert Header + LongShortPanel + AnomalyReport + CockpitWind + Tab-Leiste aus Registry; `SourceHealth` je Deep-Dive (US10,17,18–22) | B (Grundgerüst), C (Compare-Verdrahtung) |
| `frontend/src/routes.tsx` | `/deep-dive/:ticker` auf `DeepDivePage` + `/deep-dive/compare` (oder Query) verdrahten (Platzhalter ersetzen) | C |
| Tests je Komponente (`*.test.tsx`) | Smoke + Kern-Assertions, ECharts gemockt | B/C |

---

## Dispatch A — Naht, pure Logik, Tab-Registry

### Task A1: Deep-Dive-Vertrag (`contract/deepdive.ts`)

**Files:**
- Create: `frontend/src/contract/deepdive.ts`

**Interfaces:**
- Consumes: `DemoMeta` aus `contract/common.ts`; `SourceHealthMeta`, `FailedSource` aus `contract/cockpit.ts`; `Underlying`, `Wrapper`, `LongVerdict`, `ShortVerdict`, `AnomalySeverity` aus `contract/common.ts`; `Signal` aus `lib/contract.ts`.
- Produces: `DeepDiveView` und alle Unter-Typen (von Demo-Fixtures, pure Logik und allen Tab-Komponenten konsumiert).

- [ ] **Step 1: Datei mit vollständigem Vertrag schreiben** (kein Test nötig — reine Typdeklarationen; getestet durch A-Naht + pure Logik). Vollständiger Inhalt:

```ts
// Deep-Dive-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern
// denselben Vertrag, jeder View extends DemoMeta & SourceHealthMeta. Kontextabhaengige
// Bloecke (equity?/bond?/index?/commodity?) sind optional — genau der zum underlying
// passende Block ist gesetzt. signal=null => UNAVAILABLE (Spec §5.4, nie 0/neutral).
import type {
  DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict, AnomalySeverity,
} from "./common";
import type { SourceHealthMeta } from "./cockpit";
import type { Signal } from "../lib/contract";

// VerdictLens-kompatibel (components/LongShortPanel.tsx): verdict/confidence/rationale/xai.
export interface XaiDriverDTO { text: string; sign: "+" | "-"; }
export interface XaiContentDTO {
  drivers: XaiDriverDTO[];
  conflicts: string[];
  confidenceReason: string;
  whatFlips: string;
}
export interface LongLensDTO {
  verdict: LongVerdict;
  confidence: number;       // 0..1
  rationale: string;
  xai?: XaiContentDTO;
}
export interface ShortLensDTO {
  verdict: ShortVerdict;
  confidence: number;
  rationale: string;
  xai?: XaiContentDTO;
}

// Anomalie am Urteil (AnomalyContent-kompatibel, components/AnomalyReport.tsx).
export interface AnomalyDTO {
  severity: AnomalySeverity;
  outliers: string[];   // statistische Ausreisser |Z|>2.0
  conflicts: string[];  // Signalwidersprueche
}

// --- equity (US13) ---
export interface ValuationMethodDTO { name: string; low: number; high: number; } // je Methode (KGV/EV-EBITDA/DCF)
export interface EquityValuationDTO {
  methods: ValuationMethodDTO[];
  currentPrice: number | null;   // null => UNAVAILABLE
  peRatio: number | null;        // KGV
  evEbitda: number | null;       // EV/EBITDA-Multiple
}
export interface EquityQualityDTO {
  grossMarginPct: number | null;
  operatingMarginPct: number | null;
  roicPct: number | null;
  altmanZ: number | null;        // null => UNAVAILABLE
  sector: string;                // steuert Altman-Z-Schwellen (Original vs. Z'')
}
export interface EquitySignalsDTO {
  shortInterestPct: number | null;   // % der Float leerverkauft
  insiderSignal: Signal | null;      // Netto-Insiderkäufe/-verkäufe
  earningsTrend: Signal | null;      // Earnings-Revisions-Trend
  moat: "wide" | "narrow" | "none" | null; // Buffett-Burggraben
}
export interface EquityBlockDTO {
  valuation: EquityValuationDTO;
  quality: EquityQualityDTO;
  signals: EquitySignalsDTO;
}

// --- bond (US14) ---
export interface BondBlockDTO {
  modifiedDuration: number | null;  // Jahre; null => UNAVAILABLE
  creditRating: string | null;      // z. B. "AA+"
  spreadBps: number | null;         // Spread ggü. risikolos, in Basispunkten
}

// --- index (US15) ---
export interface IndexConstituentDTO { sector: string; weightPct: number; }
export interface IndexBlockDTO {
  valuationPe: number | null;       // KGV des Index
  breadthPct: number | null;        // % Titel über 200-Tage-Linie (Marktbreite)
  momentumSignal: Signal | null;
  composition: IndexConstituentDTO[]; // Sektorgewichte
}

// --- commodity / precious_metal (US16) ---
export interface SeasonalityPointDTO { month: string; avgReturnPct: number; }
export interface CrossMetalRatioDTO { name: string; value: number; note: string; } // z. B. Gold/Silber-Ratio
export interface CommodityBlockDTO {
  supplyDemandSignal: Signal | null;
  supplyDemandNote: string;
  seasonality: SeasonalityPointDTO[];
  cotIndex: number | null;          // 0..100 Perzentil-Rang (konträr: hoch=bearish)
  cotSignal: Signal | null;
  crossMetal: CrossMetalRatioDTO[]; // nur Edelmetalle; sonst []
}

// --- Futures (US33–36, nur wrapper=future) ---
export type CurveFormDTO = "contango" | "backwardation" | "flat";
export interface FuturesCurvePointDTO { contractMonth: string; price: number; } // Spot + Folgemonate
export interface FuturesBlockDTO {
  curve: FuturesCurvePointDTO[];
  form: CurveFormDTO;
  rollYieldAnnualPct: number;       // %/Jahr, Vorzeichen: <0 Contango/Gegenwind, >0 Backwardation
  expiryDate: string;               // Verfall aktueller Kontrakt (ISO)
  nextRollDate: string;             // naechster Roll-Termin (ISO)
  marginInitial: number;            // Initial-Margin in Kontraktwaehrung
  notional: number;                 // Nominalwert (fuer Hebel = notional/margin)
}

// --- Cockpit-Rueckenwind (US12) ---
export interface CockpitWindDTO {
  domainKey: string;      // z. B. "commodities" — Ziel des Rueck-Links ins Drilldown
  domainLabel: string;    // z. B. "Rohstoffe (Öl)"
  signal: Signal | null;
  note: string;           // "Öl-Signal stützt die Öl-Aktie" o. ä.
}

// --- Backtest-Kontext (US21) ---
export interface BacktestContextDTO {
  hitRatePct: number | null;   // Trefferquote des Systems fuer diesen Ticker
  sampleSize: number;          // Anzahl historischer Calls
  history: { date: string; verdict: string; correct: boolean }[];
}

export interface DeepDiveView extends DemoMeta, SourceHealthMeta {
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  price: number | null;        // aktueller Kurs; null => UNAVAILABLE
  currency: string;            // z. B. "USD"
  market: string;              // z. B. "NASDAQ", "COMEX"
  found: boolean;              // false => "nicht gefunden"-Ansicht
  long: LongLensDTO;
  short: ShortLensDTO;
  anomaly: AnomalyDTO;
  equity?: EquityBlockDTO;
  bond?: BondBlockDTO;
  index?: IndexBlockDTO;
  commodity?: CommodityBlockDTO;
  futures?: FuturesBlockDTO;   // nur wrapper=future
  cockpitWind?: CockpitWindDTO;
  backtestContext?: BacktestContextDTO;
}
```

- [ ] **Step 2: Typcheck** — Run: `cd frontend && npx tsc --noEmit`. Expected: PASS (keine Fehler in `contract/deepdive.ts`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/contract/deepdive.ts
git commit -m "feat(deepdive): Vertrag DeepDiveView mit kontextabhaengigen Bloecken

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A2: Pure Bewertungs-Bandbreite (`lib/valuationRange.ts`)

**Files:**
- Create: `frontend/src/lib/valuationRange.ts`
- Test: `frontend/src/lib/valuationRange.test.ts`

**Interfaces:**
- Consumes: `ValuationMethodDTO` aus `contract/deepdive.ts`.
- Produces: `combineValuationRange(methods)` → `{ low: number; high: number } | null`; `valuationPosition(price, low, high)` → `"undervalued" | "fair" | "overvalued"`.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { combineValuationRange, valuationPosition } from "./valuationRange";
import type { ValuationMethodDTO } from "../contract/deepdive";

const m = (name: string, low: number, high: number): ValuationMethodDTO => ({ name, low, high });

describe("combineValuationRange", () => {
  it("liefert null bei leerer Methodenliste", () => {
    expect(combineValuationRange([])).toBeNull();
  });
  it("nimmt bei einer Methode genau deren Band", () => {
    expect(combineValuationRange([m("DCF", 100, 140)])).toEqual({ low: 100, high: 140 });
  });
  it("nimmt den Median der lows/highs (kein kuenstlich breites min/max-Band)", () => {
    // lows 90/100/120 -> Median 100; highs 130/150/170 -> Median 150
    const out = combineValuationRange([m("KGV", 90, 130), m("EV", 100, 150), m("DCF", 120, 170)]);
    expect(out).toEqual({ low: 100, high: 150 });
  });
});

describe("valuationPosition", () => {
  it("unter 0.95*low => undervalued (BULLISH-Seite)", () => {
    expect(valuationPosition(90, 100, 150)).toBe("undervalued"); // 90 < 95
  });
  it("ueber 1.05*high => overvalued (BEARISH-Seite)", () => {
    expect(valuationPosition(160, 100, 150)).toBe("overvalued"); // 160 > 157.5
  });
  it("genau im Band => fair", () => {
    expect(valuationPosition(125, 100, 150)).toBe("fair");
  });
  it("knapp innerhalb der 5%-Toleranz => fair (Grenzfall)", () => {
    expect(valuationPosition(96, 100, 150)).toBe("fair");   // 96 >= 95
    expect(valuationPosition(157, 100, 150)).toBe("fair");  // 157 <= 157.5
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/valuationRange.test.ts`
Expected: FAIL ("combineValuationRange is not a function" / Modul nicht gefunden).

- [ ] **Step 3: Minimal implementieren**

```ts
import type { ValuationMethodDTO } from "../contract/deepdive";

// Bewertungs-Bandbreite ueber mehrere Methoden (KGV/EV-EBITDA/DCF). Median der lows/highs
// statt min/max — vermeidet ein kuenstlich breites Band durch einen Ausreisser
// (Standard wie valuation_range_agent._combine_methods).
export function combineValuationRange(
  methods: ValuationMethodDTO[],
): { low: number; high: number } | null {
  if (methods.length === 0) return null;
  const median = (xs: number[]): number => {
    const s = [...xs].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  };
  return { low: median(methods.map((x) => x.low)), high: median(methods.map((x) => x.high)) };
}

// Position des Kurses zum kombinierten Band (5 %-Toleranz wie valuation_range_agent._position):
// < 0.95*low => unterbewertet (BULLISH), > 1.05*high => ueberbewertet (BEARISH), sonst fair.
export function valuationPosition(
  price: number, low: number, high: number,
): "undervalued" | "fair" | "overvalued" {
  if (price < low * 0.95) return "undervalued";
  if (price > high * 1.05) return "overvalued";
  return "fair";
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/valuationRange.test.ts`
Expected: PASS (alle 7 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/valuationRange.ts frontend/src/lib/valuationRange.test.ts
git commit -m "feat(deepdive): pure Bewertungs-Bandbreite (Median + 5%-Position)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A3: Pure Altman-Z-Klassifikation (`lib/altman.ts`)

**Files:**
- Create: `frontend/src/lib/altman.ts`
- Test: `frontend/src/lib/altman.test.ts`

**Interfaces:**
- Produces: `altmanClass(z, sector)` → `"safe" | "grey" | "distress" | "unavailable" | "not_applicable"`.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { altmanClass } from "./altman";

describe("altmanClass", () => {
  it("null => unavailable (nie als 0/neutral werten)", () => {
    expect(altmanClass(null, "Technology")).toBe("unavailable");
  });
  it("Financials => not_applicable (Z nicht definiert)", () => {
    expect(altmanClass(3.5, "Banks")).toBe("not_applicable");
  });
  // Manufacturing-naher Sektor -> Original-Z (safe>2.99, distress<1.81)
  it("Manufacturing: 3.0 > 2.99 => safe", () => {
    expect(altmanClass(3.0, "Industrials")).toBe("safe");
  });
  it("Manufacturing: genau 2.99 => grey (strikt groesser fuer safe)", () => {
    expect(altmanClass(2.99, "Industrials")).toBe("grey");
  });
  it("Manufacturing: 1.5 < 1.81 => distress", () => {
    expect(altmanClass(1.5, "Materials")).toBe("distress");
  });
  // Nicht-Manufacturing (Z''): safe>2.6, distress<1.1
  it("Dienstleister: 2.7 > 2.6 => safe", () => {
    expect(altmanClass(2.7, "Technology")).toBe("safe");
  });
  it("Dienstleister: 1.0 < 1.1 => distress", () => {
    expect(altmanClass(1.0, "Technology")).toBe("distress");
  });
  it("Dienstleister: 2.0 zwischen 1.1 und 2.6 => grey", () => {
    expect(altmanClass(2.0, "Technology")).toBe("grey");
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/altman.test.ts`
Expected: FAIL ("altmanClass is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
// Altman-Z-Klassifikation (Altman 1968 / Z''). Schwellen je Unternehmenstyp wie
// quality_agent._altman_thresholds: Manufacturing-nah -> Original-Z (safe 2.99 / distress 1.81);
// sonst Z'' (2.6 / 1.1). Financials -> nicht definiert. z=null -> UNAVAILABLE (nie 0/neutral).
// Quelle: https://de.wikipedia.org/wiki/Altman-Z-Faktor
const EXCLUDED = new Set(["Financials", "Financial Services", "Banks", "Insurance"]);
const MANUFACTURING = new Set(["Industrials", "Materials", "Manufacturing", "Consumer Cyclical"]);

export function altmanClass(
  z: number | null,
  sector: string,
): "safe" | "grey" | "distress" | "unavailable" | "not_applicable" {
  if (z === null) return "unavailable";
  if (EXCLUDED.has(sector)) return "not_applicable";
  const [safe, distress] = MANUFACTURING.has(sector) ? [2.99, 1.81] : [2.6, 1.1];
  if (z > safe) return "safe";
  if (z < distress) return "distress";
  return "grey";
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/altman.test.ts`
Expected: PASS (alle 8 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/altman.ts frontend/src/lib/altman.test.ts
git commit -m "feat(deepdive): pure Altman-Z-Klassifikation (Original-Z vs. Z'')

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A4: Pure Duration-Risiko-Einstufung (`lib/duration.ts`)

**Files:**
- Create: `frontend/src/lib/duration.ts`
- Test: `frontend/src/lib/duration.test.ts`

**Interfaces:**
- Produces: `durationRisk(modifiedDuration)` → `{ level: "niedrig" | "mittel" | "hoch" | "unbekannt"; note: string }`.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { durationRisk } from "./duration";

describe("durationRisk", () => {
  it("null => unbekannt (UNAVAILABLE, nie 0)", () => {
    expect(durationRisk(null).level).toBe("unbekannt");
  });
  it("< 3 Jahre => niedrig", () => {
    expect(durationRisk(2.5).level).toBe("niedrig");
  });
  it("genau 3 => mittel (Grenze gehoert ins mittlere Band)", () => {
    expect(durationRisk(3).level).toBe("mittel");
  });
  it("3..7 => mittel", () => {
    expect(durationRisk(6).level).toBe("mittel");
  });
  it("genau 7 => hoch (Grenze gehoert ins hohe Band)", () => {
    expect(durationRisk(7).level).toBe("hoch");
  });
  it("> 7 => hoch", () => {
    expect(durationRisk(12).level).toBe("hoch");
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/duration.test.ts`
Expected: FAIL ("durationRisk is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
// Zinsrisiko aus Modified Duration (= ungefaehre %-Kursaenderung je 1 %-Punkt Renditeaenderung).
// Lueckenlose Baender: <3 J = niedrig, [3,7) = mittel, >=7 = hoch (laengere Duration -> hoehere
// Zinssensitivitaet). null = UNAVAILABLE (nie 0). Quelle: Bond-Duration (Macaulay/Modified).
export function durationRisk(
  modifiedDuration: number | null,
): { level: "niedrig" | "mittel" | "hoch" | "unbekannt"; note: string } {
  if (modifiedDuration === null) return { level: "unbekannt", note: "Duration nicht verfügbar" };
  if (modifiedDuration < 3) return { level: "niedrig", note: "geringe Zinssensitivität" };
  if (modifiedDuration < 7) return { level: "mittel", note: "moderate Zinssensitivität" };
  return { level: "hoch", note: "hohe Zinssensitivität" };
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/duration.test.ts`
Expected: PASS (6 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/duration.ts frontend/src/lib/duration.test.ts
git commit -m "feat(deepdive): pure Duration-Risiko-Einstufung (Modified Duration)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A5: Tab-Registry-Kern (`lib/deepdiveTabs.ts`)

**Files:**
- Create: `frontend/src/lib/deepdiveTabs.ts`
- Test: `frontend/src/lib/deepdiveTabs.test.ts`

**Interfaces:**
- Consumes: `DeepDiveView` aus `contract/deepdive.ts`.
- Produces: `type TabKey = "valuation" | "quality" | "signals" | "bond" | "index" | "commodity" | "futures" | "backtest"`; `tabsFor(view)` → `{ key: TabKey; label: string }[]` in fester Reihenfolge.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { tabsFor } from "./deepdiveTabs";
import type { DeepDiveView } from "../contract/deepdive";

// minimaler View-Bauer (nur Felder, die tabsFor liest)
function v(partial: Partial<DeepDiveView>): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 1, sourcesTotal: 1, failed: [],
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    price: 1, currency: "USD", market: "M", found: true,
    long: { verdict: "HOLD", confidence: 0.5, rationale: "" },
    short: { verdict: "NONE", confidence: 0.2, rationale: "" },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    ...partial,
  } as DeepDiveView;
}
const keys = (view: DeepDiveView) => tabsFor(view).map((t) => t.key);

describe("tabsFor", () => {
  it("equity: Bewertung/Qualität/Signale + Backtest, kein Futures", () => {
    expect(keys(v({ underlying: "equity", wrapper: "single" })))
      .toEqual(["valuation", "quality", "signals", "backtest"]);
  });
  it("bond: bond-Tab + Backtest", () => {
    expect(keys(v({ underlying: "bond", wrapper: "single" })))
      .toEqual(["bond", "backtest"]);
  });
  it("equity_index: index-Tab + Backtest", () => {
    expect(keys(v({ underlying: "equity_index", wrapper: "fund" })))
      .toEqual(["index", "backtest"]);
  });
  it("commodity: commodity-Tab + Backtest", () => {
    expect(keys(v({ underlying: "commodity", wrapper: "single" })))
      .toEqual(["commodity", "backtest"]);
  });
  it("precious_metal: commodity-Tab + Backtest", () => {
    expect(keys(v({ underlying: "precious_metal", wrapper: "physical_etc" })))
      .toEqual(["commodity", "backtest"]);
  });
  it("Futures-Tab nur bei wrapper=future (vor Backtest)", () => {
    expect(keys(v({ underlying: "commodity", wrapper: "future" })))
      .toEqual(["commodity", "futures", "backtest"]);
  });
  it("nicht gefunden => keine Tabs", () => {
    expect(keys(v({ found: false }))).toEqual([]);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/deepdiveTabs.test.ts`
Expected: FAIL ("tabsFor is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
import type { DeepDiveView } from "../contract/deepdive";

// Tab-Registry je underlying (Spec §7-Slice-2-Zeile, Konzept §4.5: Tab-Set kontextabhaengig).
// equity != bond != index != commodity. Futures-Tab nur bei wrapper=future. Backtest immer zuletzt.
export type TabKey =
  | "valuation" | "quality" | "signals"
  | "bond" | "index" | "commodity"
  | "futures" | "backtest";

export interface TabDef { key: TabKey; label: string; }

const BY_UNDERLYING: Record<DeepDiveView["underlying"], TabDef[]> = {
  equity: [
    { key: "valuation", label: "Bewertung" },
    { key: "quality", label: "Qualität" },
    { key: "signals", label: "Signale" },
  ],
  bond: [{ key: "bond", label: "Anleihe" }],
  equity_index: [{ key: "index", label: "Index" }],
  commodity: [{ key: "commodity", label: "Rohstoff" }],
  precious_metal: [{ key: "commodity", label: "Edelmetall" }],
};

export function tabsFor(view: DeepDiveView): TabDef[] {
  if (!view.found) return [];
  const tabs = [...BY_UNDERLYING[view.underlying]];
  if (view.wrapper === "future") tabs.push({ key: "futures", label: "Futures" });
  tabs.push({ key: "backtest", label: "Backtest-Kontext" });
  return tabs;
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/deepdiveTabs.test.ts`
Expected: PASS (7 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/deepdiveTabs.ts frontend/src/lib/deepdiveTabs.test.ts
git commit -m "feat(deepdive): Tab-Registry je underlying (Futures-Tab nur bei future)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A6: Demo-Fixtures (`data/demo/deepdive.ts`)

**Files:**
- Create: `frontend/src/data/demo/deepdive.ts`

**Interfaces:**
- Consumes: alle DTOs aus `contract/deepdive.ts`.
- Produces: `demoDeepDive(ticker: string): DeepDiveView` — kennt `AAPL`, `GC=F`, `TLT`, `SPY`, `CL=F`, `4GLD`; unbekannt → `notFound`-View.

> **Fachliche Annahmen (Demo-Werte, im Code als solche markiert):** Werte sind plausible Größenordnungen, nicht exakt. AAPL: KGV ~30, EV/EBITDA ~22, ROIC ~50 %, Altman-Z ~6 (safe, Sektor "Technology"→Z''), Moat "wide", Short-Interest ~0.8 %. GC=F: Contango leicht (Roll-Yield −3,1 %/Jahr, wie Konzept §5.1), Margin/Hebel ~33×. TLT (20J-Treasury-ETF, hier als bond-Beispiel): Modified Duration ~16 J → „hoch", Rating "AA+", Spread ~0 bps (Staatsanleihe). SPY: KGV ~24, Breadth ~58 %, Tech-Gewicht ~30 %. CL=F (WTI-Öl-Future): Contango, COT-Index ~72, Cockpit-Wind „Rohstoffe" bullish. 4GLD (physisches Gold-ETC): kein Roll, Hebel 1×, BUY-Urteil (gegen GC=F HOLD → zeigt Wrapper-Unterschied im Vergleich, Konzept §5.2). AAPL trägt zusätzlich einen UNAVAILABLE-Sub-Agenten (z. B. Earnings-Trend `null`) + eine `failed`-Quelle, damit der UNAVAILABLE-Pfad real getestet wird (Spec §1).

- [ ] **Step 1: Datei mit vollständigen Fixtures schreiben** (kein eigener Test — durch A7-Naht-Test abgedeckt). Vollständiger Inhalt:

```ts
// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Mehrere Ticker quer ueber underlying x wrapper; unbekannt -> "nicht gefunden"-View.
import type { DeepDiveView } from "../../contract/deepdive";

function notFound(ticker: string): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 0, sourcesTotal: 0, failed: [],
    ticker, name: "Unbekannter Titel", underlying: "equity", wrapper: "single",
    price: null, currency: "", market: "", found: false,
    long: { verdict: "NONE", confidence: 0, rationale: "Kein Titel zu diesem Ticker gefunden." },
    short: { verdict: "NONE", confidence: 0, rationale: "Kein Titel zu diesem Ticker gefunden." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
  };
}

function aapl(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 5, sourcesTotal: 6,
    // Bewusst ein ausgefallener Sub-Agent -> UNAVAILABLE-Pfad (Spec §1/§5.4).
    failed: [{ key: "Earnings-Trend (Stub)", reason: "Revisions-Feed noch nicht angebunden" }],
    ticker: "AAPL", name: "Apple Inc.", underlying: "equity", wrapper: "single",
    price: 232.1, currency: "USD", market: "NASDAQ", found: true,
    long: {
      verdict: "HOLD", confidence: 0.58,
      rationale: "Qualität top, aber Bewertung am oberen Rand der Bandbreite.",
      xai: {
        drivers: [
          { text: "Wide Moat + ROIC ~50 % rechtfertigt Prämie", sign: "+" },
          { text: "Kurs über kombinierter Bewertungs-Bandbreite", sign: "-" },
        ],
        conflicts: ["Qualität bullish vs. Bewertung bearish"],
        confidenceReason: "1 Quelle UNAVAILABLE (Earnings-Trend) senkt Konfidenz",
        whatFlips: "Kursrücksetzer in die Bandbreite ODER Margenausweitung",
      },
    },
    short: {
      verdict: "NONE", confidence: 0.18,
      rationale: "Kein tragfähiger Short: Qualität zu hoch, kein Bilanzrisiko.",
    },
    anomaly: { severity: "low", outliers: [], conflicts: ["Qualität vs. Bewertung"] },
    equity: {
      valuation: {
        methods: [
          { name: "KGV-Multiple", low: 170, high: 210 },
          { name: "EV/EBITDA-Multiple", low: 180, high: 220 },
          { name: "DCF", low: 160, high: 205 },
        ],
        currentPrice: 232.1, peRatio: 30.5, evEbitda: 22.4,
      },
      quality: {
        grossMarginPct: 45.2, operatingMarginPct: 30.1, roicPct: 49.8,
        altmanZ: 6.1, sector: "Technology", // Z'' -> safe
      },
      signals: {
        shortInterestPct: 0.8, insiderSignal: "neutral",
        earningsTrend: null,   // UNAVAILABLE (Stub) — NICHT 0/neutral
        moat: "wide",
      },
    },
    backtestContext: {
      hitRatePct: 64, sampleSize: 25,
      history: [
        { date: "2025-09", verdict: "BUY", correct: true },
        { date: "2025-12", verdict: "HOLD", correct: true },
        { date: "2026-03", verdict: "BUY", correct: false },
      ],
    },
  };
}

function gcFuture(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "GC=F", name: "Gold", underlying: "precious_metal", wrapper: "future",
    price: 2380, currency: "USD", market: "COMEX", found: true,
    long: {
      verdict: "HOLD", confidence: 0.47,
      rationale: "Roll-Gegenwind (Contango) bremst Long; Makro stützt.",
      xai: {
        drivers: [
          { text: "Makro-Regime AUFSCHWUNG stützt Edelmetall", sign: "+" },
          { text: "Contango → Roll-Yield −3,1 %/Jahr Gegenwind", sign: "-" },
        ],
        conflicts: ["Top-Down bullish vs. Roll-Struktur bearish"],
        confidenceReason: "Starkes Gegensignal aus der Roll-Struktur",
        whatFlips: "Wechsel in Backwardation ODER Realzins fällt",
      },
    },
    short: { verdict: "NONE", confidence: 0.22, rationale: "Kein tragfähiger Short: Realzins-Druck nicht stark." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    commodity: {
      supplyDemandSignal: "neutral", supplyDemandNote: "Minenangebot stabil, Notenbankkäufe stützen",
      seasonality: [
        { month: "Jan", avgReturnPct: 1.2 }, { month: "Feb", avgReturnPct: 0.4 },
        { month: "Aug", avgReturnPct: 1.8 }, { month: "Sep", avgReturnPct: 2.1 },
      ],
      cotIndex: null, cotSignal: null,  // COT fuer Gold hier UNAVAILABLE (Demo)
      crossMetal: [{ name: "Gold/Silber-Ratio", value: 84, note: "über langfristigem Mittel (~70) → Silber relativ günstig" }],
    },
    futures: {
      curve: [
        { contractMonth: "Spot", price: 2380 },
        { contractMonth: "Jun", price: 2392 },
        { contractMonth: "Sep", price: 2410 },
        { contractMonth: "Dez", price: 2431 },
      ],
      form: "contango",
      rollYieldAnnualPct: -3.1,  // Contango -> negativ (Gegenwind), Konzept §5.1
      expiryDate: "2026-06-26", nextRollDate: "2026-06-26",
      marginInitial: 7150, notional: 238000, // Hebel ~33x
    },
    cockpitWind: {
      domainKey: "commodities", domainLabel: "Rohstoffe (Edelmetall)",
      signal: "neutral", note: "Edelmetall-Treiber im Cockpit aktuell neutral.",
    },
    backtestContext: { hitRatePct: 55, sampleSize: 18, history: [] },
  };
}

function tltBond(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "TLT", name: "20+ Jahre US-Staatsanleihen", underlying: "bond", wrapper: "fund",
    price: 88.4, currency: "USD", market: "NASDAQ", found: true,
    long: {
      verdict: "BUY", confidence: 0.61,
      rationale: "Lange Duration profitiert von erwartet fallenden Zinsen.",
      xai: {
        drivers: [{ text: "Zinswende erwartet → Kursgewinn bei langer Duration", sign: "+" }],
        conflicts: [], confidenceReason: "klares Makro-Signal, geringe Streuung",
        whatFlips: "Inflationsüberraschung nach oben",
      },
    },
    short: { verdict: "NONE", confidence: 0.2, rationale: "Kein Short bei fallender-Zins-Erwartung." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    bond: { modifiedDuration: 16.2, creditRating: "AA+", spreadBps: 5 }, // Treasury: hohe Duration, ~0 Spread
    backtestContext: { hitRatePct: 60, sampleSize: 14, history: [] },
  };
}

function spyIndex(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 4, sourcesTotal: 4, failed: [],
    ticker: "SPY", name: "S&P 500 ETF", underlying: "equity_index", wrapper: "fund",
    price: 542.3, currency: "USD", market: "NYSE Arca", found: true,
    long: {
      verdict: "HOLD", confidence: 0.52,
      rationale: "Breit getragen, aber Bewertung erhöht.",
      xai: {
        drivers: [
          { text: "Breadth 58 % → mehrheitlich über 200-Tage-Linie", sign: "+" },
          { text: "Index-KGV 24 über historischem Schnitt", sign: "-" },
        ],
        conflicts: [], confidenceReason: "ausgewogene Treiber", whatFlips: "Breadth-Verschlechterung < 50 %",
      },
    },
    short: { verdict: "NONE", confidence: 0.25, rationale: "Kein Index-Short im Aufschwung." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    index: {
      valuationPe: 24.1, breadthPct: 58, momentumSignal: "bullish",
      composition: [
        { sector: "Technologie", weightPct: 30 }, { sector: "Finanzen", weightPct: 13 },
        { sector: "Gesundheit", weightPct: 12 }, { sector: "Zyklischer Konsum", weightPct: 11 },
        { sector: "Sonstige", weightPct: 34 },
      ],
    },
    backtestContext: { hitRatePct: 58, sampleSize: 30, history: [] },
  };
}

function clFuture(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 4,
    failed: [{ key: "Saisonalität (Stub)", reason: "historische Monatsrenditen noch nicht angebunden" }],
    ticker: "CL=F", name: "Rohöl WTI", underlying: "commodity", wrapper: "future",
    price: 78.5, currency: "USD", market: "NYMEX", found: true,
    long: {
      verdict: "HOLD", confidence: 0.49,  // <0.50 -> auto-HOLD-Badge sichtbar
      rationale: "Angebotsdisziplin stützt, aber Roll-Gegenwind und COT-Extrem dämpfen.",
      xai: {
        drivers: [
          { text: "OPEC+-Angebotsdisziplin", sign: "+" },
          { text: "COT-Index 72 → Spekulanten stark long (konträr bearish)", sign: "-" },
        ],
        conflicts: ["Fundamental bullish vs. Positionierung bearish"],
        confidenceReason: "Konfidenz <0.50 → auto-HOLD",
        whatFlips: "COT-Entspannung ODER Backwardation",
      },
    },
    short: { verdict: "HOLD", confidence: 0.33, rationale: "Schwacher Short-Ansatz über COT-Extrem." }, // <0.35 -> Cash-Bias
    anomaly: { severity: "medium", outliers: ["COT-Index im 90. Perzentil"], conflicts: ["Fundamental vs. Positionierung"] },
    commodity: {
      supplyDemandSignal: "bullish", supplyDemandNote: "OPEC+ hält Förderung knapp, Nachfrage robust",
      seasonality: [],  // UNAVAILABLE (Stub) — bewusst leer
      cotIndex: 72, cotSignal: "bearish", // konträr: hoher COT-Index -> bearish (wie cot_agent._cot_signal)
      crossMetal: [],
    },
    futures: {
      curve: [
        { contractMonth: "Spot", price: 78.5 },
        { contractMonth: "Aug", price: 78.9 },
        { contractMonth: "Sep", price: 79.4 },
        { contractMonth: "Okt", price: 79.8 },
      ],
      form: "contango", rollYieldAnnualPct: -5.4,
      expiryDate: "2026-07-22", nextRollDate: "2026-07-17",
      marginInitial: 6800, notional: 78500, // Hebel ~11.5x
    },
    cockpitWind: {
      domainKey: "commodities", domainLabel: "Rohstoffe (Öl)",
      signal: "bullish", note: "Öl-Signal aus dem Cockpit stützt die Öl-These (Rückenwind).",
    },
    backtestContext: { hitRatePct: 51, sampleSize: 22, history: [] },
  };
}

function goldEtc(): DeepDiveView {
  return {
    isDemo: true, sourcesActive: 3, sourcesTotal: 3, failed: [],
    ticker: "4GLD", name: "Xetra-Gold (physisch)", underlying: "precious_metal", wrapper: "physical_etc",
    price: 71.2, currency: "EUR", market: "XETRA", found: true,
    long: {
      verdict: "BUY", confidence: 0.58,  // bewusst BUY (vs. GC=F HOLD) -> Wrapper-Unterschied im Vergleich
      rationale: "Kein Roll-Gegenwind, voll besichert — saubere Gold-Long-Hülle.",
      xai: {
        drivers: [
          { text: "Makro stützt Edelmetall", sign: "+" },
          { text: "Kein Roll-Yield-Gegenwind (physisch)", sign: "+" },
        ],
        conflicts: [], confidenceReason: "keine Roll-Belastung → höhere Konfidenz als Future",
        whatFlips: "Realzins steigt deutlich",
      },
    },
    short: { verdict: "NONE", confidence: 0.2, rationale: "Kein Short auf physisches Gold sinnvoll." },
    anomaly: { severity: "none", outliers: [], conflicts: [] },
    commodity: {
      supplyDemandSignal: "neutral", supplyDemandNote: "Minenangebot stabil, Notenbankkäufe stützen",
      seasonality: [{ month: "Aug", avgReturnPct: 1.8 }, { month: "Sep", avgReturnPct: 2.1 }],
      cotIndex: null, cotSignal: null,
      crossMetal: [{ name: "Gold/Silber-Ratio", value: 84, note: "über langfristigem Mittel (~70)" }],
    },
    // KEIN futures-Block (physical_etc) — Futures-Tab erscheint nicht.
    backtestContext: { hitRatePct: 57, sampleSize: 12, history: [] },
  };
}

const FIXTURES: Record<string, () => DeepDiveView> = {
  AAPL: aapl, "GC=F": gcFuture, TLT: tltBond, SPY: spyIndex, "CL=F": clFuture, "4GLD": goldEtc,
};

export function demoDeepDive(ticker: string): DeepDiveView {
  const make = FIXTURES[ticker.toUpperCase()] ?? FIXTURES[ticker];
  return make ? make() : notFound(ticker);
}
```

- [ ] **Step 2: Typcheck** — Run: `cd frontend && npx tsc --noEmit`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/demo/deepdive.ts
git commit -m "feat(deepdive): Demo-Fixtures (AAPL/GC=F/TLT/SPY/CL=F/4GLD + notFound)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A7: Die Naht (`data/deepdive.ts`) + Naht-Test

**Files:**
- Create: `frontend/src/data/deepdive.ts`
- Test: `frontend/src/data/deepdive.test.ts`

**Interfaces:**
- Consumes: `demoDeepDive` aus `data/demo/deepdive.ts`; `ApiDeps` aus `data/apiDeps.ts`.
- Produces: `loadDeepDive(ticker: string, deps?: ApiDeps): Promise<DeepDiveView>`.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { loadDeepDive } from "./deepdive";

describe("loadDeepDive (Tausch-Naht)", () => {
  it("liefert fuer bekannten Ticker einen Demo-View (isDemo:true, found:true)", async () => {
    const v = await loadDeepDive("AAPL");
    expect(v.isDemo).toBe(true);
    expect(v.found).toBe(true);
    expect(v.ticker).toBe("AAPL");
    expect(v.underlying).toBe("equity");
  });
  it("liefert fuer GC=F den Futures-Block + wrapper=future", async () => {
    const v = await loadDeepDive("GC=F");
    expect(v.wrapper).toBe("future");
    expect(v.futures).toBeTruthy();
  });
  it("liefert fuer unbekannten Ticker eine nicht-gefunden-Ansicht (found:false)", async () => {
    const v = await loadDeepDive("ZZZZ");
    expect(v.found).toBe(false);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/data/deepdive.test.ts`
Expected: FAIL ("loadDeepDive is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer den Deep-Dive. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { DeepDiveView } from "../contract/deepdive";
import { demoDeepDive } from "./demo/deepdive";
import type { ApiDeps } from "./apiDeps";

export async function loadDeepDive(ticker: string, _deps?: ApiDeps): Promise<DeepDiveView> {
  return demoDeepDive(ticker);
  // return fetchDeepDive(ticker, _deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/data/deepdive.test.ts`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/deepdive.ts frontend/src/data/deepdive.test.ts
git commit -m "feat(deepdive): Tausch-Naht loadDeepDive(ticker) (Demo heute, echt vorbereitet)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Dispatch B — Header, Long/Short/XAI/Anomalie, kontextabhängige Tabs, Health, Cockpit-Wind, Backtest

> **Gemeinsame Test-Konvention für Dispatch B/C:** Jede `*.test.tsx`, die eine Komponente mit Charts oder Routing rendert, beginnt mit `vi.mock("echarts-for-react", () => ({ default: () => null }))` und rendert (falls Links/Navigation) in `<MemoryRouter>`. Tab-Komponenten erhalten ihren Block als Prop (z. B. `<EquityTabs block={view.equity!} />`) und sind ohne Router testbar.

### Task B1: Deep-Dive-Header (`components/deepdive/DeepDiveHeader.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/DeepDiveHeader.tsx`
- Test: `frontend/src/components/deepdive/DeepDiveHeader.test.tsx`

**Interfaces:**
- Consumes: `UnderlyingWrapperBadge`; `UnavailableField`; `DeepDiveView` (Felder `name`/`ticker`/`underlying`/`wrapper`/`price`/`currency`/`market`).
- Produces: `DeepDiveHeader({ view, onCompare }: { view: DeepDiveView; onCompare?: () => void })`.

**Strukturvorgabe:** Zeile 1 — `{ticker} · {name}`. Zeile 2 — `<UnderlyingWrapperBadge underlying wrapper />`. Zeile 3 — Kurs (`{price} {currency}`, bei `price===null` → `<UnavailableField/>`) · `Markt: {market}` · Button „⤳ vergleichen mit" (ruft `onCompare`).

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DeepDiveHeader } from "./DeepDiveHeader";
import { demoDeepDive } from "../../data/demo/deepdive";

describe("DeepDiveHeader", () => {
  it("zeigt Ticker, Name, beide Etiketten und Kurs/Markt", () => {
    render(<DeepDiveHeader view={demoDeepDive("GC=F")} />);
    expect(screen.getByText(/GC=F/)).toBeInTheDocument();
    expect(screen.getByText(/Gold/)).toBeInTheDocument();
    expect(screen.getByText("Edelmetall")).toBeInTheDocument(); // underlying-Badge
    expect(screen.getByText("Future")).toBeInTheDocument();     // wrapper-Badge
    expect(screen.getByText(/COMEX/)).toBeInTheDocument();
    expect(screen.getByText(/2380/)).toBeInTheDocument();
  });
  it("ruft onCompare beim Klick auf 'vergleichen'", () => {
    const onCompare = vi.fn();
    render(<DeepDiveHeader view={demoDeepDive("GC=F")} onCompare={onCompare} />);
    fireEvent.click(screen.getByRole("button", { name: /vergleichen/i }));
    expect(onCompare).toHaveBeenCalledOnce();
  });
  it("zeigt 'nicht verfügbar' wenn price null", () => {
    render(<DeepDiveHeader view={demoDeepDive("ZZZZ")} />);
    expect(screen.getByText(/nicht verfügbar/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/DeepDiveHeader.test.tsx`
Expected: FAIL (Modul/Component nicht gefunden).

- [ ] **Step 3: Implementieren**

```tsx
import type { DeepDiveView } from "../../contract/deepdive";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { UnavailableField } from "../UnavailableField";

// Header (Konzept §4.5): beide Etiketten + Kurs/Markt + "vergleichen mit"-Einstieg.
export function DeepDiveHeader({ view, onCompare }: { view: DeepDiveView; onCompare?: () => void }) {
  return (
    <header className="space-y-2 border-b border-slate-200 pb-3 dark:border-slate-700">
      <h1 className="text-xl font-bold">{view.ticker} · {view.name}</h1>
      <UnderlyingWrapperBadge underlying={view.underlying} wrapper={view.wrapper} />
      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
        <span>
          Kurs: {view.price === null
            ? <UnavailableField reason="Kurs nicht verfügbar" />
            : <span className="font-medium">{view.price} {view.currency}</span>}
        </span>
        <span>· Markt: {view.market || "—"}</span>
        {onCompare && (
          <button type="button" onClick={onCompare} className="text-sky-600 underline">
            ⤳ vergleichen mit
          </button>
        )}
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/DeepDiveHeader.test.tsx`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/DeepDiveHeader.tsx frontend/src/components/deepdive/DeepDiveHeader.test.tsx
git commit -m "feat(deepdive): Header mit underlying x wrapper + Kurs/Markt + vergleichen

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B2: Cockpit-Wind (`components/deepdive/CockpitWind.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/CockpitWind.tsx`
- Test: `frontend/src/components/deepdive/CockpitWind.test.tsx`

**Interfaces:**
- Consumes: `CockpitWindDTO` aus `contract/deepdive.ts`; `SignalBadge`; `Link` aus `react-router-dom`.
- Produces: `CockpitWind({ wind }: { wind: CockpitWindDTO })`.

**Strukturvorgabe:** Box mit Label „Cockpit-Rücken-/Gegenwind", `domainLabel`, `<SignalBadge signal={wind.signal} />`, `note`, und `<Link to={"/cockpit/" + wind.domainKey}>` mit Text „↗ ins Cockpit-Drilldown" (US12: Rück-Link).

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CockpitWind } from "./CockpitWind";

describe("CockpitWind", () => {
  it("zeigt Domänen-Label, Note und einen Link ins Drilldown", () => {
    render(
      <MemoryRouter>
        <CockpitWind wind={{ domainKey: "commodities", domainLabel: "Rohstoffe (Öl)", signal: "bullish", note: "Öl stützt." }} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Rohstoffe \(Öl\)/)).toBeInTheDocument();
    expect(screen.getByText(/Öl stützt\./)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Cockpit/i });
    expect(link).toHaveAttribute("href", "/cockpit/commodities");
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/CockpitWind.test.tsx`
Expected: FAIL (Component nicht gefunden).

- [ ] **Step 3: Implementieren**

```tsx
import { Link } from "react-router-dom";
import type { CockpitWindDTO } from "../../contract/deepdive";
import { SignalBadge } from "../SignalBadge";

// Cockpit-Signal als Ruecken-/Gegenwind im Deep-Dive + Rueck-Link ins Drilldown (US12, Konzept §3).
export function CockpitWind({ wind }: { wind: CockpitWindDTO }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
      <div className="text-xs uppercase tracking-wide text-slate-500">Cockpit-Rücken-/Gegenwind</div>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <span className="font-medium">{wind.domainLabel}:</span>
        <SignalBadge signal={wind.signal} />
        <Link to={`/cockpit/${wind.domainKey}`} className="text-sky-600 underline">↗ ins Cockpit-Drilldown</Link>
      </div>
      <p className="mt-1 text-slate-600 dark:text-slate-300">{wind.note}</p>
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/CockpitWind.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/CockpitWind.tsx frontend/src/components/deepdive/CockpitWind.test.tsx
git commit -m "feat(deepdive): Cockpit-Ruecken-/Gegenwind mit Rueck-Link ins Drilldown (US12)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B3: Equity-Tabs (`components/deepdive/tabs/EquityTabs.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/EquityTabs.tsx`
- Test: `frontend/src/components/deepdive/tabs/EquityTabs.test.tsx`

**Interfaces:**
- Consumes: `EquityBlockDTO` aus `contract/deepdive.ts`; pure `combineValuationRange`/`valuationPosition` aus `lib/valuationRange.ts`; `altmanClass` aus `lib/altman.ts`; `SignalBadge`; `UnavailableField`.
- Produces: drei Render-Funktionen als eine Komponente mit `tab`-Prop: `EquityTabs({ block, tab }: { block: EquityBlockDTO; tab: "valuation" | "quality" | "signals" })`.

**Strukturvorgabe:**
- `tab==="valuation"`: KGV (`peRatio`), EV/EBITDA (`evEbitda`), Methoden-Tabelle (`methods`), kombiniertes Band aus `combineValuationRange` + Position aus `valuationPosition` (bei `currentPrice===null` → „Position: nicht verfügbar"). Jeder `null`-Wert → `<UnavailableField/>`.
- `tab==="quality"`: Bruttomarge/operative Marge/ROIC (`null` → `UnavailableField`), Altman-Z als Zahl + Klasse aus `altmanClass(altmanZ, sector)` (deutsche Labels: safe→„solvent", grey→„Grauzone", distress→„Insolvenzrisiko", unavailable→`UnavailableField`, not_applicable→„nicht anwendbar (Finanzsektor)").
- `tab==="signals"`: Short-Interest % (`null`→`UnavailableField`), Insider (`SignalBadge`), Earnings-Trend (`SignalBadge` — bei `null` zeigt `signalToVisual` bereits „nicht verfügbar"), Moat (wide→„breit", narrow→„schmal", none→„keiner", `null`→`UnavailableField`).

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EquityTabs } from "./EquityTabs";
import { demoDeepDive } from "../../../data/demo/deepdive";

const block = demoDeepDive("AAPL").equity!;

describe("EquityTabs", () => {
  it("Bewertung: zeigt KGV, EV/EBITDA und kombinierte Bandbreite", () => {
    render(<EquityTabs block={block} tab="valuation" />);
    expect(screen.getByText(/30\.5/)).toBeInTheDocument(); // KGV
    expect(screen.getByText(/22\.4/)).toBeInTheDocument(); // EV/EBITDA
    // kombiniertes Band (Median lows 160/170/180 -> 170; highs 205/210/220 -> 210)
    expect(screen.getByText(/170/)).toBeInTheDocument();
    expect(screen.getByText(/210/)).toBeInTheDocument();
  });
  it("Qualität: Altman-Z 6.1 (Technology -> Z'') => solvent", () => {
    render(<EquityTabs block={block} tab="quality" />);
    expect(screen.getByText(/6\.1/)).toBeInTheDocument();
    expect(screen.getByText(/solvent/i)).toBeInTheDocument();
  });
  it("Signale: Earnings-Trend null => nicht verfügbar (NICHT neutral/0)", () => {
    render(<EquityTabs block={block} tab="signals" />);
    expect(screen.getByText(/Moat/i)).toBeInTheDocument();
    expect(screen.getAllByText(/nicht verfügbar/i).length).toBeGreaterThanOrEqual(1);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/EquityTabs.test.tsx`
Expected: FAIL (Component nicht gefunden).

- [ ] **Step 3: Implementieren** (vollständig)

```tsx
import type { EquityBlockDTO } from "../../../contract/deepdive";
import { combineValuationRange, valuationPosition } from "../../../lib/valuationRange";
import { altmanClass } from "../../../lib/altman";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

const ALTMAN_LABEL: Record<string, string> = {
  safe: "solvent", grey: "Grauzone", distress: "Insolvenzrisiko",
  not_applicable: "nicht anwendbar (Finanzsektor)",
};
const MOAT_LABEL: Record<string, string> = { wide: "breit", narrow: "schmal", none: "keiner" };

function num(v: number | null, suffix = ""): React.ReactNode {
  return v === null ? <UnavailableField /> : <span className="font-medium">{v}{suffix}</span>;
}

// Kontextabhaengige equity-Tabs (US13): Bewertung/Qualitaet/Signale. Pure-Logik aus lib/.
export function EquityTabs({ block, tab }: { block: EquityBlockDTO; tab: "valuation" | "quality" | "signals" }) {
  if (tab === "valuation") {
    const range = combineValuationRange(block.valuation.methods);
    const pos = range && block.valuation.currentPrice !== null
      ? valuationPosition(block.valuation.currentPrice, range.low, range.high) : null;
    return (
      <div className="space-y-3 text-sm">
        <div>KGV: {num(block.valuation.peRatio)}</div>
        <div>EV/EBITDA: {num(block.valuation.evEbitda)}</div>
        <table className="w-full text-left">
          <thead><tr className="text-xs uppercase text-slate-500"><th>Methode</th><th>tief</th><th>hoch</th></tr></thead>
          <tbody>
            {block.valuation.methods.map((m) => (
              <tr key={m.name}><td>{m.name}</td><td>{m.low}</td><td>{m.high}</td></tr>
            ))}
          </tbody>
        </table>
        {range && (
          <div className="rounded bg-slate-50 p-2 dark:bg-slate-800">
            Kombinierte Bandbreite: <span className="font-medium">{range.low}–{range.high}</span>
            {pos && <> · Position: <span className="font-medium">{pos === "undervalued" ? "unterbewertet" : pos === "overvalued" ? "überbewertet" : "fair"}</span></>}
            {!pos && <> · Position: nicht verfügbar</>}
          </div>
        )}
      </div>
    );
  }
  if (tab === "quality") {
    const cls = altmanClass(block.quality.altmanZ, block.quality.sector);
    return (
      <div className="space-y-2 text-sm">
        <div>Bruttomarge: {num(block.quality.grossMarginPct, " %")}</div>
        <div>Operative Marge: {num(block.quality.operatingMarginPct, " %")}</div>
        <div>ROIC: {num(block.quality.roicPct, " %")}</div>
        <div>
          Altman-Z: {num(block.quality.altmanZ)}{" "}
          {cls === "unavailable" ? <UnavailableField reason="Altman-Z nicht verfügbar" />
            : <span className="font-medium">({ALTMAN_LABEL[cls]})</span>}
        </div>
      </div>
    );
  }
  // signals
  return (
    <div className="space-y-2 text-sm">
      <div>Short-Interest: {num(block.signals.shortInterestPct, " %")}</div>
      <div>Insider: <SignalBadge signal={block.signals.insiderSignal} /></div>
      <div>Earnings-Trend: <SignalBadge signal={block.signals.earningsTrend} /></div>
      <div>Moat: {block.signals.moat === null ? <UnavailableField /> : <span className="font-medium">{MOAT_LABEL[block.signals.moat]}</span>}</div>
    </div>
  );
}
```

> **Prüfen:** `signalToVisual(null)` in `lib/display.ts` muss „nicht verfügbar" o. ä. liefern (UNAVAILABLE-Pfad). Falls es stattdessen leer/neutral rendert, im Signale-Tab `block.signals.earningsTrend === null ? <UnavailableField/> : <SignalBadge .../>` verwenden, damit der Test (`nicht verfügbar`) grün wird. (Bestehendes Verhalten zuerst lesen.)

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/EquityTabs.test.tsx`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/EquityTabs.tsx frontend/src/components/deepdive/tabs/EquityTabs.test.tsx
git commit -m "feat(deepdive): equity-Tabs Bewertung/Qualitaet/Signale (US13)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B4: Bond-Tab (`components/deepdive/tabs/BondTab.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/BondTab.tsx`
- Test: `frontend/src/components/deepdive/tabs/BondTab.test.tsx`

**Interfaces:**
- Consumes: `BondBlockDTO`; `durationRisk` aus `lib/duration.ts`; `UnavailableField`.
- Produces: `BondTab({ block }: { block: BondBlockDTO })`.

**Strukturvorgabe:** Modified Duration (`null`→`UnavailableField`) + Risiko-Level/Note aus `durationRisk`; Credit-Rating (`null`→`UnavailableField`); Spread in bps (`null`→`UnavailableField`).

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BondTab } from "./BondTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("BondTab", () => {
  it("zeigt Duration (16.2, hoch), Rating und Spread", () => {
    render(<BondTab block={demoDeepDive("TLT").bond!} />);
    expect(screen.getByText(/16\.2/)).toBeInTheDocument();
    expect(screen.getByText(/hoch/i)).toBeInTheDocument();   // Duration-Risiko
    expect(screen.getByText(/AA\+/)).toBeInTheDocument();    // Rating
    expect(screen.getByText(/5/)).toBeInTheDocument();       // Spread bps
  });
  it("zeigt 'nicht verfügbar' bei fehlender Duration", () => {
    render(<BondTab block={{ modifiedDuration: null, creditRating: null, spreadBps: null }} />);
    expect(screen.getAllByText(/nicht verfügbar/i).length).toBeGreaterThanOrEqual(2);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/BondTab.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { BondBlockDTO } from "../../../contract/deepdive";
import { durationRisk } from "../../../lib/duration";
import { UnavailableField } from "../../UnavailableField";

// bond-Variante (US14): Duration (Zinsrisiko), Credit-Rating (Ausfallrisiko), Spread. Getrennt.
export function BondTab({ block }: { block: BondBlockDTO }) {
  const risk = durationRisk(block.modifiedDuration);
  return (
    <div className="space-y-2 text-sm">
      <div>
        Modified Duration: {block.modifiedDuration === null
          ? <UnavailableField reason="Duration nicht verfügbar" />
          : <span className="font-medium">{block.modifiedDuration} J · Risiko {risk.level} ({risk.note})</span>}
      </div>
      <div>Credit-Rating: {block.creditRating === null ? <UnavailableField /> : <span className="font-medium">{block.creditRating}</span>}</div>
      <div>Spread: {block.spreadBps === null ? <UnavailableField /> : <span className="font-medium">{block.spreadBps} bps</span>}</div>
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/BondTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/BondTab.tsx frontend/src/components/deepdive/tabs/BondTab.test.tsx
git commit -m "feat(deepdive): bond-Tab Duration/Rating/Spread (US14)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B5: Index-Tab (`components/deepdive/tabs/IndexTab.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/IndexTab.tsx`
- Test: `frontend/src/components/deepdive/tabs/IndexTab.test.tsx`

**Interfaces:**
- Consumes: `IndexBlockDTO`; `SignalBadge`; `UnavailableField`.
- Produces: `IndexTab({ block }: { block: IndexBlockDTO })`.

**Strukturvorgabe:** Index-KGV (`null`→`UnavailableField`), Breadth % (`null`→`UnavailableField`), Momentum (`SignalBadge`), Sektorkomposition als Liste `{sector}: {weightPct} %`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IndexTab } from "./IndexTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("IndexTab", () => {
  it("zeigt KGV, Breadth, Momentum und Sektorgewichte", () => {
    render(<IndexTab block={demoDeepDive("SPY").index!} />);
    expect(screen.getByText(/24\.1/)).toBeInTheDocument();   // KGV
    expect(screen.getByText(/58/)).toBeInTheDocument();      // Breadth
    expect(screen.getByText(/Technologie/)).toBeInTheDocument();
    expect(screen.getByText(/30 %/)).toBeInTheDocument();    // Tech-Gewicht
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/IndexTab.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { IndexBlockDTO } from "../../../contract/deepdive";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

// index-Variante (US15): Bewertung, Breadth (Marktbreite), Momentum, Sektorkomposition —
// zeigt, ob ein Index breit getragen oder von wenigen Titeln getrieben ist.
export function IndexTab({ block }: { block: IndexBlockDTO }) {
  return (
    <div className="space-y-2 text-sm">
      <div>Index-KGV: {block.valuationPe === null ? <UnavailableField /> : <span className="font-medium">{block.valuationPe}</span>}</div>
      <div>Breadth: {block.breadthPct === null ? <UnavailableField /> : <span className="font-medium">{block.breadthPct} % über 200-Tage-Linie</span>}</div>
      <div>Momentum: <SignalBadge signal={block.momentumSignal} /></div>
      <div>
        <div className="text-xs uppercase text-slate-500">Sektorkomposition</div>
        <ul>{block.composition.map((c) => <li key={c.sector}>{c.sector}: {c.weightPct} %</li>)}</ul>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/IndexTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/IndexTab.tsx frontend/src/components/deepdive/tabs/IndexTab.test.tsx
git commit -m "feat(deepdive): index-Tab Bewertung/Breadth/Momentum/Komposition (US15)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B6: Commodity-Tab (`components/deepdive/tabs/CommodityTab.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/CommodityTab.tsx`
- Test: `frontend/src/components/deepdive/tabs/CommodityTab.test.tsx`

**Interfaces:**
- Consumes: `CommodityBlockDTO`; `SignalBadge`; `UnavailableField`.
- Produces: `CommodityTab({ block }: { block: CommodityBlockDTO })`.

**Strukturvorgabe:** Supply/Demand (`SignalBadge` + Note); Saisonalität als Liste (leer → `UnavailableField` „Saisonalität nicht verfügbar"); COT-Index + COT-Signal (`null`→`UnavailableField`; Hinweis „konträr: hoher Index = bearish"); Cross-Metal-Ratios als Liste (nur wenn nicht leer — bei Öl leer, dann ausblenden).

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CommodityTab } from "./CommodityTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("CommodityTab", () => {
  it("Öl (CL=F): COT-Index 72 + bearish, Saisonalität leer => nicht verfügbar", () => {
    render(<CommodityTab block={demoDeepDive("CL=F").commodity!} />);
    expect(screen.getByText(/72/)).toBeInTheDocument();             // COT-Index
    expect(screen.getByText(/konträr/i)).toBeInTheDocument();       // konträre Erklärung
    expect(screen.getByText(/nicht verfügbar/i)).toBeInTheDocument(); // leere Saisonalität
  });
  it("Gold (GC=F): Cross-Metal-Ratio sichtbar, COT null => nicht verfügbar", () => {
    render(<CommodityTab block={demoDeepDive("GC=F").commodity!} />);
    expect(screen.getByText(/Gold\/Silber-Ratio/)).toBeInTheDocument();
    expect(screen.getByText(/84/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/CommodityTab.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { CommodityBlockDTO } from "../../../contract/deepdive";
import { SignalBadge } from "../../SignalBadge";
import { UnavailableField } from "../../UnavailableField";

// commodity/precious-Variante (US16): Supply/Demand, Saisonalitaet, COT (konträr) bzw.
// Cross-Metal-Ratios. COT-Index hoch => Spekulanten extrem long => konträr bearish (cot_agent).
export function CommodityTab({ block }: { block: CommodityBlockDTO }) {
  return (
    <div className="space-y-3 text-sm">
      <div>Supply/Demand: <SignalBadge signal={block.supplyDemandSignal} /> <span className="text-slate-600 dark:text-slate-300">— {block.supplyDemandNote}</span></div>
      <div>
        <div className="text-xs uppercase text-slate-500">Saisonalität</div>
        {block.seasonality.length === 0
          ? <UnavailableField reason="Saisonalität nicht verfügbar" />
          : <ul>{block.seasonality.map((s) => <li key={s.month}>{s.month}: {s.avgReturnPct >= 0 ? "+" : ""}{s.avgReturnPct} %</li>)}</ul>}
      </div>
      <div>
        COT-Index: {block.cotIndex === null
          ? <UnavailableField reason="COT nicht verfügbar" />
          : <span className="font-medium">{block.cotIndex}/100 · <SignalBadge signal={block.cotSignal} /> <span className="text-xs text-slate-500">(konträr: hoher Index = bearish)</span></span>}
      </div>
      {block.crossMetal.length > 0 && (
        <div>
          <div className="text-xs uppercase text-slate-500">Cross-Metal-Ratios</div>
          <ul>{block.crossMetal.map((r) => <li key={r.name}>{r.name}: <span className="font-medium">{r.value}</span> — {r.note}</li>)}</ul>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/CommodityTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/CommodityTab.tsx frontend/src/components/deepdive/tabs/CommodityTab.test.tsx
git commit -m "feat(deepdive): commodity/precious-Tab Supply-Demand/Saisonalitaet/COT/Cross-Metal (US16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B7: Backtest-Kontext-Tab (`components/deepdive/tabs/BacktestContextTab.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/BacktestContextTab.tsx`
- Test: `frontend/src/components/deepdive/tabs/BacktestContextTab.test.tsx`

**Interfaces:**
- Consumes: `BacktestContextDTO`; `UnavailableField`.
- Produces: `BacktestContextTab({ ctx }: { ctx: BacktestContextDTO })`.

**Strukturvorgabe:** Trefferquote % (`null`→`UnavailableField`) + Stichprobengröße; Historie als Liste `{date}: {verdict} {✓/✗}` (leer → Hinweis „keine Historie für diesen Ticker").

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestContextTab } from "./BacktestContextTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("BacktestContextTab", () => {
  it("zeigt Trefferquote, Stichprobe und Historie", () => {
    render(<BacktestContextTab ctx={demoDeepDive("AAPL").backtestContext!} />);
    expect(screen.getByText(/64/)).toBeInTheDocument();   // Trefferquote
    expect(screen.getByText(/25/)).toBeInTheDocument();   // Stichprobe
    expect(screen.getByText(/2025-09/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/BacktestContextTab.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { BacktestContextDTO } from "../../../contract/deepdive";
import { UnavailableField } from "../../UnavailableField";

// Backtester-Kontext fuer DIESEN Ticker (US21): wie treffsicher war das System hier bisher.
export function BacktestContextTab({ ctx }: { ctx: BacktestContextDTO }) {
  return (
    <div className="space-y-2 text-sm">
      <div>
        Trefferquote: {ctx.hitRatePct === null
          ? <UnavailableField reason="keine Backtest-Daten" />
          : <span className="font-medium">{ctx.hitRatePct} %</span>} ({ctx.sampleSize} historische Calls)
      </div>
      {ctx.history.length === 0
        ? <p className="text-slate-500">Keine Einzel-Historie für diesen Ticker.</p>
        : <ul>{ctx.history.map((h, i) => <li key={i}>{h.date}: {h.verdict} {h.correct ? "✓" : "✗"}</li>)}</ul>}
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/BacktestContextTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/BacktestContextTab.tsx frontend/src/components/deepdive/tabs/BacktestContextTab.test.tsx
git commit -m "feat(deepdive): Backtest-Kontext-Tab je Ticker (US21)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B8: DeepDivePage-Grundgerüst (`pages/DeepDivePage.tsx`)

**Files:**
- Create: `frontend/src/pages/DeepDivePage.tsx`
- Test: `frontend/src/pages/DeepDivePage.test.tsx`

**Interfaces:**
- Consumes: `useView`; `loadDeepDive`; `tabsFor`/`TabKey` aus `lib/deepdiveTabs.ts`; `DeepDiveHeader`, `CockpitWind`, `EquityTabs`, `BondTab`, `IndexTab`, `CommodityTab`, `BacktestContextTab`; `LongShortPanel` (+ `VerdictLens`); `AnomalyReport` (+ `AnomalyContent`); `SourceHealth`; `DemoBadge`; `useParams` aus `react-router-dom`.
- Produces: `DeepDivePage({ loader }?: { loader?: (ticker: string) => Promise<DeepDiveView> })` — liest `:ticker` aus der Route, mappt View → `LongShortPanel`-Props, rendert Tab-Leiste aus `tabsFor`. (Futures-Tab + Compare in Dispatch C ergänzt.)

> **Mapping-Hinweis:** Der Vertrag (`LongLensDTO`/`ShortLensDTO`/`AnomalyDTO`) ist strukturell identisch mit `VerdictLens`/`AnomalyContent` — direkt als Props übergeben (`long={view.long}` etc.). `useView` braucht einen **stabilen** Loader: `const load = useCallback(() => loader(ticker), [loader, ticker])`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { DeepDivePage } from "./DeepDivePage";
import { loadDeepDive } from "../data/deepdive";

vi.mock("echarts-for-react", () => ({ default: () => null }));

function renderAt(ticker: string) {
  return render(
    <MemoryRouter initialEntries={[`/deep-dive/${ticker}`]}>
      <Routes><Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} /></Routes>
    </MemoryRouter>,
  );
}

describe("DeepDivePage", () => {
  it("equity (AAPL): Header, Long/Short-Panel, Anomalie, equity-Tabs, KEIN Futures-Tab", async () => {
    renderAt("AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
    expect(screen.getByText("LONG-LINSE")).toBeInTheDocument();
    expect(screen.getByText("SHORT-LINSE")).toBeInTheDocument();
    expect(screen.getByText(/Anomalie-Schwere/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Bewertung/ })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Futures/ })).not.toBeInTheDocument();
    expect(screen.getByText("Demo-Daten")).toBeInTheDocument();
  });
  it("bond (TLT): bond-Tab statt equity-Tabs", async () => {
    renderAt("TLT");
    await waitFor(() => expect(screen.getByRole("tab", { name: /Anleihe/ })).toBeInTheDocument());
    expect(screen.queryByRole("tab", { name: /Qualität/ })).not.toBeInTheDocument();
  });
  it("Tab-Wechsel rendert den Qualität-Inhalt (Altman-Z)", async () => {
    renderAt("AAPL");
    await waitFor(() => screen.getByRole("tab", { name: /Qualität/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Qualität/ }));
    expect(screen.getByText(/Altman-Z/)).toBeInTheDocument();
  });
  it("Cockpit-Wind sichtbar bei CL=F (Öl-Rückenwind)", async () => {
    renderAt("CL=F");
    await waitFor(() => expect(screen.getByText(/Rohstoffe \(Öl\)/)).toBeInTheDocument());
  });
  it("nicht gefunden (ZZZZ): Hinweis statt Tabs", async () => {
    renderAt("ZZZZ");
    await waitFor(() => expect(screen.getByText(/nicht gefunden/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: FAIL (Component nicht gefunden).

- [ ] **Step 3: Implementieren** (Futures-Tab-Case + Compare folgen in C — hier `default`-Fall offen lassen)

```tsx
import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import { useView } from "../data/useView";
import { loadDeepDive } from "../data/deepdive";
import { tabsFor, type TabKey } from "../lib/deepdiveTabs";
import type { DeepDiveView } from "../contract/deepdive";
import { DeepDiveHeader } from "../components/deepdive/DeepDiveHeader";
import { CockpitWind } from "../components/deepdive/CockpitWind";
import { LongShortPanel } from "../components/LongShortPanel";
import { AnomalyReport } from "../components/AnomalyReport";
import { SourceHealth } from "../components/SourceHealth";
import { DemoBadge } from "../components/DemoBadge";
import { EquityTabs } from "../components/deepdive/tabs/EquityTabs";
import { BondTab } from "../components/deepdive/tabs/BondTab";
import { IndexTab } from "../components/deepdive/tabs/IndexTab";
import { CommodityTab } from "../components/deepdive/tabs/CommodityTab";
import { BacktestContextTab } from "../components/deepdive/tabs/BacktestContextTab";

function TabContent({ tab, view }: { tab: TabKey; view: DeepDiveView }) {
  switch (tab) {
    case "valuation": return <EquityTabs block={view.equity!} tab="valuation" />;
    case "quality":   return <EquityTabs block={view.equity!} tab="quality" />;
    case "signals":   return <EquityTabs block={view.equity!} tab="signals" />;
    case "bond":      return <BondTab block={view.bond!} />;
    case "index":     return <IndexTab block={view.index!} />;
    case "commodity": return <CommodityTab block={view.commodity!} />;
    case "backtest":  return <BacktestContextTab ctx={view.backtestContext!} />;
    // case "futures": -> Dispatch C ergaenzt FuturesTab
    default:          return <p className="text-slate-500">Tab folgt.</p>;
  }
}

// Deep-Dive pro Anlage (US10,17,18–22): laedt per :ticker ueber die Tausch-Naht.
export function DeepDivePage({ loader = loadDeepDive }: { loader?: (ticker: string) => Promise<DeepDiveView> }) {
  const { ticker = "" } = useParams();
  const load = useCallback(() => loader(ticker), [loader, ticker]);
  const { data, loading, error } = useView(load);
  const [active, setActive] = useState<TabKey | null>(null);

  if (loading) return <p className="text-slate-500">Lädt …</p>;
  if (error || !data) return <p className="text-red-600">{error ?? "Keine Daten"}</p>;
  if (!data.found) return (
    <div className="space-y-2">
      <DeepDiveHeader view={data} />
      <p className="text-slate-600">Kein Titel zu „{data.ticker}" gefunden. Bitte anderen Ticker suchen.</p>
    </div>
  );

  const tabs = tabsFor(data);
  const current = active ?? tabs[0]?.key ?? null;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <DeepDiveHeader view={data} />
        <DemoBadge isDemo={data.isDemo} />
      </div>
      <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />
      <LongShortPanel long={data.long} short={data.short} />
      <AnomalyReport anomaly={data.anomaly} />
      {data.cockpitWind && <CockpitWind wind={data.cockpitWind} />}

      <div role="tablist" className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-700">
        {tabs.map((t) => (
          <button
            key={t.key} role="tab" aria-selected={t.key === current}
            onClick={() => setActive(t.key)}
            className={`px-3 py-1.5 text-sm ${t.key === current ? "border-b-2 border-sky-500 font-medium" : "text-slate-500"}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {current && <div className="pt-2">{<TabContent tab={current} view={data} />}</div>}
    </section>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: PASS (5 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DeepDivePage.tsx frontend/src/pages/DeepDivePage.test.tsx
git commit -m "feat(deepdive): DeepDivePage (Header/Long-Short/Anomalie/Health/Tabs je underlying)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Dispatch C — Futures-Tab, Vergleichsmodus, Routing-Verdrahtung

### Task C1: Futures-Tab (`components/deepdive/tabs/FuturesTab.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/tabs/FuturesTab.tsx`
- Test: `frontend/src/components/deepdive/tabs/FuturesTab.test.tsx`

**Interfaces:**
- Consumes: `FuturesBlockDTO`; `LineCurve` aus `charts/LineCurve`; `rollYieldVisual`, `leverageFactor` aus `lib/futures.ts`.
- Produces: `FuturesTab({ block }: { block: FuturesBlockDTO })`.

**Strukturvorgabe (Konzept §5.1):** Terminkurve über `LineCurve` (`series=[{name:"Terminkurve", points: curve.map(p => ({x:p.contractMonth, y:p.price}))}]`); Form (contango/backwardation/flat) als Wort; Roll-Yield über `rollYieldVisual(rollYieldAnnualPct, form)` (Label+Pfeil+Farbe, Vorzeichen explizit als `%/Jahr`); Verfall + nächster Roll als Daten; Margin + Hebel über `leverageFactor(notional, marginInitial)` als `≈ N×`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FuturesTab } from "./FuturesTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

vi.mock("echarts-for-react", () => ({ default: () => null }));

describe("FuturesTab", () => {
  it("GC=F: Contango, negativer Roll-Yield (Gegenwind), Verfall/Roll, Hebel ~33x", () => {
    render(<FuturesTab block={demoDeepDive("GC=F").futures!} />);
    expect(screen.getByText(/CONTANGO/i)).toBeInTheDocument();
    expect(screen.getByText(/-3\.1/)).toBeInTheDocument();          // Roll-Yield %/Jahr
    expect(screen.getByText(/Gegenwind/i)).toBeInTheDocument();     // rollYieldVisual-Label
    expect(screen.getByText(/2026-06-26/)).toBeInTheDocument();     // Verfall
    expect(screen.getByText(/33/)).toBeInTheDocument();             // Hebel (238000/7150 ≈ 33.3)
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/FuturesTab.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { FuturesBlockDTO } from "../../../contract/deepdive";
import { LineCurve } from "../../charts/LineCurve";
import { rollYieldVisual, leverageFactor } from "../../../lib/futures";

// Futures-Tab (US33–36, Konzept §5.1): Terminkurve (Contango/Backwardation) + Roll-Yield
// (Vorzeichen/Richtung benannt) + Verfall/Roll + Margin/Hebel (Hebel = Nominal/Margin).
export function FuturesTab({ block }: { block: FuturesBlockDTO }) {
  const roll = rollYieldVisual(block.rollYieldAnnualPct, block.form);
  const lev = leverageFactor(block.notional, block.marginInitial);
  return (
    <div className="space-y-4 text-sm">
      <LineCurve
        series={[{ name: "Terminkurve", points: block.curve.map((p) => ({ x: p.contractMonth, y: p.price })) }]}
        height={200}
      />
      <div>Form: <span className="font-medium uppercase">{block.form}</span></div>
      <div>
        Roll-Yield: <span className={`font-medium ${roll.colorClass}`}>
          {block.rollYieldAnnualPct >= 0 ? "+" : ""}{block.rollYieldAnnualPct} %/Jahr {roll.arrow}
        </span> <span className="text-slate-500">({roll.label})</span>
      </div>
      <div>Verfall aktueller Kontrakt: <span className="font-medium">{block.expiryDate}</span></div>
      <div>Nächster Roll-Termin: <span className="font-medium">{block.nextRollDate}</span></div>
      <div>Margin (Initial): <span className="font-medium">{block.marginInitial} </span> → Hebel ≈ {lev.toFixed(1)}×</div>
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/tabs/FuturesTab.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/tabs/FuturesTab.tsx frontend/src/components/deepdive/tabs/FuturesTab.test.tsx
git commit -m "feat(deepdive): Futures-Tab Terminkurve/Roll-Yield/Verfall/Hebel (US33–36)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task C2: Futures-Tab in die Page einhängen

**Files:**
- Modify: `frontend/src/pages/DeepDivePage.tsx`
- Modify: `frontend/src/pages/DeepDivePage.test.tsx`

**Interfaces:**
- Consumes: `FuturesTab` aus C1.

- [ ] **Step 1: Failing test ergänzen** (in `DeepDivePage.test.tsx` neuen Fall hinzufügen)

```tsx
  it("future (GC=F): Futures-Tab vorhanden und rendert Terminkurve-Inhalt", async () => {
    renderAt("GC=F");
    await waitFor(() => screen.getByRole("tab", { name: /Futures/ }));
    fireEvent.click(screen.getByRole("tab", { name: /Futures/ }));
    expect(screen.getByText(/Roll-Yield/)).toBeInTheDocument();
  });
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: FAIL (Futures-Tab zeigt „Tab folgt." statt Roll-Yield).

- [ ] **Step 3: Page anpassen** — Import ergänzen und `default`-Fall durch Futures-Case ersetzen:

```tsx
import { FuturesTab } from "../components/deepdive/tabs/FuturesTab";
```

In `TabContent` den Kommentar/`default` ersetzen durch:

```tsx
    case "futures":   return <FuturesTab block={view.futures!} />;
    default:          return null;
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: PASS (6 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/DeepDivePage.tsx frontend/src/pages/DeepDivePage.test.tsx
git commit -m "feat(deepdive): Futures-Tab in DeepDivePage eingehaengt (nur wrapper=future)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task C3: Vergleichsmodus (`components/deepdive/CompareView.tsx`)

**Files:**
- Create: `frontend/src/components/deepdive/CompareView.tsx`
- Test: `frontend/src/components/deepdive/CompareView.test.tsx`

**Interfaces:**
- Consumes: `DeepDiveView`; `UnderlyingWrapperBadge`; `rollYieldVisual`, `leverageFactor` aus `lib/futures.ts`; `verdictToVisual` aus `lib/judgment.ts`.
- Produces: `CompareView({ left, right }: { left: DeepDiveView; right: DeepDiveView })` — zwei Wrapper desselben underlying nebeneinander.

**Strukturvorgabe (Konzept §5.2):** Vergleichstabelle mit Zeilen: Basiswert (`name`), Hülle (`UnderlyingWrapperBadge`), Roll-Yield (Future: `rollYieldVisual` + `%/Jahr`; ohne `futures` → „— (kein Roll)"), Hebel (Future: `leverageFactor` `≈ N×`; sonst „1× (voll besichert)"), Long-Urteil (`verdictToVisual` + Konfidenz %). Spalten = `left`/`right`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CompareView } from "./CompareView";
import { demoDeepDive } from "../../data/demo/deepdive";

describe("CompareView (Gold-Future vs. physisches ETC)", () => {
  it("zeigt Roll-Yield/Hebel-Unterschied und beide Urteile", () => {
    render(<CompareView left={demoDeepDive("GC=F")} right={demoDeepDive("4GLD")} />);
    expect(screen.getByText(/-3\.1/)).toBeInTheDocument();       // Future-Roll
    expect(screen.getByText(/kein Roll/i)).toBeInTheDocument();  // ETC ohne Roll
    expect(screen.getByText(/voll besichert/i)).toBeInTheDocument(); // ETC Hebel 1x
    expect(screen.getByText("HOLD")).toBeInTheDocument();        // GC=F Long-Urteil
    expect(screen.getByText("BUY")).toBeInTheDocument();         // 4GLD Long-Urteil
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/deepdive/CompareView.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { DeepDiveView } from "../../contract/deepdive";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { rollYieldVisual, leverageFactor } from "../../lib/futures";
import { verdictToVisual } from "../../lib/judgment";

function rollCell(v: DeepDiveView) {
  if (!v.futures) return <span className="text-slate-500">— (kein Roll)</span>;
  const r = rollYieldVisual(v.futures.rollYieldAnnualPct, v.futures.form);
  return <span className={r.colorClass}>{v.futures.rollYieldAnnualPct >= 0 ? "+" : ""}{v.futures.rollYieldAnnualPct} %/Jahr {r.arrow}</span>;
}
function levCell(v: DeepDiveView) {
  if (!v.futures) return <span>1× (voll besichert)</span>;
  return <span>≈ {leverageFactor(v.futures.notional, v.futures.marginInitial).toFixed(1)}×</span>;
}
function verdictCell(v: DeepDiveView) {
  const vis = verdictToVisual(v.long.verdict);
  return <span className={vis.colorClass}>{vis.label} {Math.round(v.long.confidence * 100)} %</span>;
}

// Vergleichsmodus (US11, Konzept §5.2): gleicher underlying, zwei wrapper nebeneinander.
export function CompareView({ left, right }: { left: DeepDiveView; right: DeepDiveView }) {
  const cols = [left, right];
  const Row = ({ label, render }: { label: string; render: (v: DeepDiveView) => React.ReactNode }) => (
    <tr><th className="py-1 pr-4 text-left font-medium text-slate-500">{label}</th>{cols.map((c) => <td key={c.ticker} className="py-1 pr-4">{render(c)}</td>)}</tr>
  );
  return (
    <table className="text-sm">
      <thead><tr><th /> {cols.map((c) => <th key={c.ticker} className="py-1 pr-4 text-left">{c.ticker}</th>)}</tr></thead>
      <tbody>
        <Row label="Basiswert" render={(v) => v.name} />
        <Row label="Hülle" render={(v) => <UnderlyingWrapperBadge underlying={v.underlying} wrapper={v.wrapper} />} />
        <Row label="Roll-Yield" render={rollCell} />
        <Row label="Hebel" render={levCell} />
        <Row label="Long-Urteil" render={verdictCell} />
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/deepdive/CompareView.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/deepdive/CompareView.tsx frontend/src/components/deepdive/CompareView.test.tsx
git commit -m "feat(deepdive): Vergleichsmodus zweier Wrapper (Roll-Yield/Hebel/Urteil) (US11)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task C4: Vergleich in die Page + Routing-Verdrahtung

**Files:**
- Modify: `frontend/src/pages/DeepDivePage.tsx`
- Modify: `frontend/src/pages/DeepDivePage.test.tsx`
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/routes.test.tsx`

**Interfaces:**
- Consumes: `CompareView` aus C3; `useSearchParams` aus `react-router-dom`.
- Produces: Vergleich wird über `?vergleich=<TICKER>` aktiviert; der Header-Button „vergleichen mit" setzt für Future-Wrapper standardmäßig das physische Pendant (GC=F ↔ 4GLD), sonst öffnet er ein kleines Eingabefeld. (Demo-einfach: Button setzt `?vergleich`-Param auf ein sinnvolles Default-Gegenstück; CompareView lädt den zweiten View über `loadDeepDive`.)

> **Vereinfachung (YAGNI):** Kein eigenes Routing für Compare. Der Vergleich ist ein **Zustand der DeepDivePage**: Header-`onCompare` setzt `?vergleich=<defaultGegenstueck>`; die Page liest den Param, lädt den zweiten View per `loadDeepDive` und rendert `CompareView` oberhalb der Tabs. Default-Gegenstück-Map (nur Demo): `{ "GC=F": "4GLD", "4GLD": "GC=F" }`; fehlt ein Eintrag, zeigt der Button ein Textfeld zum Tickern.

- [ ] **Step 1: Failing test ergänzen** (in `DeepDivePage.test.tsx`)

```tsx
  it("Vergleich: ?vergleich=4GLD zeigt CompareView mit beiden Tickern", async () => {
    render(
      <MemoryRouter initialEntries={["/deep-dive/GC=F?vergleich=4GLD"]}>
        <Routes><Route path="/deep-dive/:ticker" element={<DeepDivePage loader={loadDeepDive} />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/Vergleich/i)).toBeInTheDocument());
    expect(screen.getByText("4GLD")).toBeInTheDocument();
    expect(screen.getByText(/kein Roll/i)).toBeInTheDocument();
  });
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: FAIL (CompareView nicht gerendert).

- [ ] **Step 3: Page erweitern** — Imports + Vergleichs-Zustand:

```tsx
import { useParams, useSearchParams } from "react-router-dom";
import { useEffect } from "react";
import { CompareView } from "../components/deepdive/CompareView";

const COMPARE_DEFAULT: Record<string, string> = { "GC=F": "4GLD", "4GLD": "GC=F" };
```

In der Komponente (nach dem Haupt-`useView`), zweiten View laden, wenn `?vergleich` gesetzt:

```tsx
  const [params, setParams] = useSearchParams();
  const compareTicker = params.get("vergleich");
  const [compareView, setCompareView] = useState<DeepDiveView | null>(null);
  useEffect(() => {
    if (!compareTicker) { setCompareView(null); return; }
    let cancelled = false;
    loader(compareTicker).then((v) => { if (!cancelled) setCompareView(v); });
    return () => { cancelled = true; };
  }, [compareTicker, loader]);

  const onCompare = () => {
    const partner = COMPARE_DEFAULT[data?.ticker ?? ""] ?? "4GLD";
    setParams({ vergleich: partner });
  };
```

`DeepDiveHeader` mit `onCompare={onCompare}` aufrufen, und oberhalb der Tab-Leiste einfügen:

```tsx
      {compareView && (
        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <div className="mb-2 text-sm font-semibold">Vergleich — gleicher Basiswert, zwei Hüllen</div>
          <CompareView left={data} right={compareView} />
        </div>
      )}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/pages/DeepDivePage.test.tsx`
Expected: PASS (7 Tests grün).

- [ ] **Step 5: Routing verdrahten** — in `routes.tsx` den Platzhalter ersetzen:

```tsx
import { DeepDivePage } from "./pages/DeepDivePage";
```

Zeile `<Route path="/deep-dive/:ticker" element={<PlaceholderPage title="Deep-Dive" />} />` ersetzen durch:

```tsx
        <Route path="/deep-dive/:ticker" element={<DeepDivePage />} />
```

- [ ] **Step 6: Routing-Test ergänzen** (in `routes.test.tsx`, ECharts mocken)

```tsx
  it("/deep-dive/AAPL rendert die DeepDivePage", async () => {
    renderAt("/deep-dive/AAPL"); // bestehender Render-Helfer der Datei
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
  });
```

> **Hinweis:** Falls `routes.test.tsx` noch keinen ECharts-Mock am Dateikopf hat, `vi.mock("echarts-for-react", () => ({ default: () => null }))` ergänzen; den vorhandenen Render-Helfer der Datei verwenden (nicht neu erfinden).

- [ ] **Step 7: Tests laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/routes.test.tsx src/pages/DeepDivePage.test.tsx`
Expected: PASS.

- [ ] **Step 8: Voller Lauf + Typcheck**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: PASS (alle Tests grün, keine Typfehler).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/DeepDivePage.tsx frontend/src/pages/DeepDivePage.test.tsx frontend/src/routes.tsx frontend/src/routes.test.tsx
git commit -m "feat(deepdive): Vergleichsmodus + Routing /deep-dive/:ticker verdrahtet (US10/US11)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task C5: Logbuch + Folge-Aufgaben (`docs/open_todos.md`)

**Files:**
- Modify: `docs/open_todos.md`

> **Kein Test** (reine Doku, AGENTS.md §5). Slice 2 ist ein PR — der Logbuch-Eintrag dokumentiert die Umsetzung und die echten Backend-Endpunkte als Folge-Aufgaben. **Nicht** direkt auf master committen; dieser Commit gehört in den Slice-2-PR.

- [ ] **Step 1: Eintrag ergänzen** (passend zum bestehenden Logbuch-Stil) — abgehakter Slice-2-Eintrag mit `Lösung:`-Hinweis + neue Folge-Aufgaben:

```markdown
- [x] **Frontend Slice 2 — Deep-Dive** (Konzept §2.2/§2.3/§2.7, Spec §7). Lösung: Deep-Dive pro Anlage über die Tausch-Naht `loadDeepDive(ticker)` (Demo-Fixtures AAPL/GC=F/TLT/SPY/CL=F/4GLD + notFound). Header (underlying×wrapper + Kurs/Markt + vergleichen), LongShortPanel + XAI + Schwellen-Flags + AnomalyReport, kontextabhängige Tabs je underlying (equity/bond/index/commodity, Futures nur bei wrapper=future) über pure Tab-Registry `tabsFor`, Sub-Agenten-Health, Cockpit-Wind (US12), Backtest-Kontext (US21), Vergleichsmodus (US11). Pure getestete Logik: `combineValuationRange`/`valuationPosition`, `altmanClass`, `durationRisk`, `tabsFor`. US10–22 + US33–36 abgedeckt.
  - [ ] **Folge: echte Deep-Dive-Endpunkte** — `data/api/deepdive.ts` (`fetchDeepDive`) statt Demo; Naht-Zeile in `data/deepdive.ts` tauschen (Backend liefert underlying/wrapper, Long+Short+XAI, Futures-Roll-Kennzahlen, Sub-Agenten-Health). Lösungsansatz: bestehende stock_deep_dive-Chiefs (equity/bond/index/commodity/precious) hinter einen API-Endpunkt hängen, der den DeepDiveView-Vertrag erfüllt.
  - [ ] **Folge: COT/Saisonalität/Earnings-Trend echt** — aktuell teils UNAVAILABLE/Demo; an echte Quellen anbinden (siehe Stubs-Initiative im Logbuch).
```

- [ ] **Step 2: Commit** (in den Slice-2-PR, nicht direkt auf master)

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Frontend Slice 2 (Deep-Dive) + Folge-Aufgaben protokolliert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec-Coverage (US10–22 + US33–36, Spec §10 Slice-2-Zeile):**

| US | Inhalt | Task(s) |
|---|---|---|
| US10 | Ticker → Header beide Etiketten | A6/A7 (Naht), B1 (Header), C4 (Routing `:ticker`) |
| US11 | Gold-Future vs. physisches ETC vergleichen (Roll-Yield/Hebel) | C3 (CompareView), C4 (Verdrahtung), A6 (4GLD-Fixture) |
| US12 | Öl-Signal aus Cockpit als Rücken-/Gegenwind + Link | B2 (CockpitWind), B8 (in Page) |
| US13 | equity Bewertung/Qualität/Signale + Bandbreite | B3 (EquityTabs), A2 (Bandbreite), A3 (Altman) |
| US14 | bond Duration/Rating/Spread | B4 (BondTab), A4 (Duration) |
| US15 | index Bewertung/Breadth/Momentum/Komposition | B5 (IndexTab) |
| US16 | commodity/precious Supply-Demand/Saisonalität/COT/Cross-Metal | B6 (CommodityTab) |
| US17 | Sub-Agenten-Health je Deep-Dive | B8 (SourceHealth in Page) + A6 (failed-Quellen in Fixtures) |
| US18 | Long+Short nebeneinander je Konfidenz | B8 (LongShortPanel in Page) |
| US19 | XAI je Urteil | B8 (XaiPanel via LongShortPanel) + A6 (xai in Fixtures) |
| US20 | <0.50 auto-HOLD, <0.35 Cash-Bias | B8 (ThresholdBadges via LongShortPanel) + A6 (CL=F-Konfidenzen 0.49/0.33) |
| US21 | Backtest-Kontext für Ticker | B7 (BacktestContextTab), B8 (in Page) |
| US22 | Anomalie-Report am Urteil | B8 (AnomalyReport in Page) + A6 (anomaly in Fixtures) |
| US33 | Terminkurve Contango/Backwardation | C1 (FuturesTab `LineCurve`) |
| US34 | Roll-Yield Vorzeichen | C1 (`rollYieldVisual`) |
| US35 | Verfall + nächster Roll | C1 (FuturesTab) |
| US36 | Margin + effektiver Hebel | C1 (`leverageFactor`) |

Architektur-Vorgaben: Tausch-Naht (A1/A6/A7), pure getestete Logik (A2–A5), kontextabhängige Tab-Registry (A5), TDD je Task, UNAVAILABLE-Pfad (AAPL Earnings-Trend `null`, CL=F Saisonalität leer, GC=F COT `null`, failed-Quellen), keine magischen Zahlen ohne Begründung (Schwellen kommentiert + Backend-Quelle), Charts gemockt, Loader stabil via `useCallback`. Keine Lücke.

**2. Placeholder-Scan:** Kein „TBD/TODO/später/Beispiel-Logik". Alle Code-Schritte enthalten vollständigen Code; alle Tests vollständige Assertions.

**3. Typ-Konsistenz:** `DeepDiveView`-Felder (A1) werden überall identisch benannt (`underlying`/`wrapper`/`price`/`currency`/`market`/`found`/`long`/`short`/`anomaly`/`equity`/`bond`/`index`/`commodity`/`futures`/`cockpitWind`/`backtestContext`). `TabKey`-Werte (A5) deckungsgleich mit `TabContent`-Cases (B8/C2). `LongLensDTO`/`ShortLensDTO`/`AnomalyDTO` strukturell kompatibel zu `VerdictLens`/`AnomalyContent` (B8-Mapping ohne Adapter). Pure-Funktionsnamen identisch zwischen Definition (A2–A5) und Nutzung (B3/B4/C1/C3). `demoDeepDive` (A6) liefert genau die in Tests erwarteten Werte (Altman-Z 6.1, Band 170–210, Roll −3.1, Hebel ~33). `equity_index` als underlying-Key in `BY_UNDERLYING` (A5) entspricht `contract/common.ts`.

---

## Dispatch-Gruppierung

- **Dispatch A (Fundament: Naht + pure Logik + Registry-Gerüst):** A1 (Vertrag), A2 (Bewertungs-Bandbreite), A3 (Altman-Z), A4 (Duration), A5 (Tab-Registry), A6 (Demo-Fixtures), A7 (Naht `loadDeepDive`). — Voneinander testbar, blockieren B/C.
- **Dispatch B (Page-Kern: Header + Long/Short/XAI/Anomalie + kontextabhängige Tabs + Health + Cockpit-Wind + Backtest):** B1 (Header), B2 (CockpitWind), B3 (EquityTabs), B4 (BondTab), B5 (IndexTab), B6 (CommodityTab), B7 (BacktestContextTab), B8 (DeepDivePage). — B3–B7 sind unabhängig voneinander (parallelisierbar), B8 hängt von B1–B7 + A5.
- **Dispatch C (Futures + Vergleich + Routing):** C1 (FuturesTab), C2 (Futures in Page), C3 (CompareView), C4 (Vergleich + Routing + voller Lauf), C5 (Logbuch). — Hängt von B8.
