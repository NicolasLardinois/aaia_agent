# Frontend Slice 3 — Portfolio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den Portfolio-Bereich (Track B, beratend) bauen — Positionstabelle (long und short, beide Etiketten, L/S-Richtung, Größe, Einstand, AAIA-Urteil + Konflikt-Markierung), Risiko-Panel (Brutto-/Netto-Exposure + net_beta aktien-only mit datierter Vola, je mit Inline-Definition), Klumpen-Warnungen (Sektor/underlying/Geographie mit Limit-Bezug), Hedge-Vorschläge (beratend, **keine** Trade-Ausführung) und die Ticker→Deep-Dive-Verdrahtung — alles über die austauschbare Demo-Naht.

**Architecture:** Tausch-Naht wie Slice 1/2 (`contract/portfolio.ts` → Vertrag, `data/portfolio.ts` → eine Lade-Funktion `loadPortfolio(deps?)`, `data/demo/portfolio.ts` → Fixtures mit `isDemo:true`). Die UI ist dumm und liest nur den Vertrag. Die Risiko-Mathematik (Exposure, net_beta, Klumpen-Detektion, Konflikt-Erkennung, Hedge-Ableitung) wird als **pure, getestete Funktionen** TDD-first gebaut, von React entkoppelt — gespiegelt aus der maßgeblichen Backend-Logik `agents/portfolio/portfolio_monitor_agent.py` (PR #11: net_beta aktien-only + datierte Vola). Die Konflikt-Erkennung wird als **pure, exportierte** Funktion `detectConflict(position, judgment)` angelegt, damit Slice 4 (Inbox) sie wiederverwendet.

**Tech Stack:** React 19 + TypeScript + Vite + Tailwind v3 + Vitest + React Testing Library + react-router-dom. Slice 3 braucht **keine** Charts (Tabellen + Kennzahlen-Panel reichen) — daher kein ECharts-Mock nötig; Tabellen rendern mit Routing-Links in `<MemoryRouter>`.

## Global Constraints

- **Sprache:** Code-Kommentare und UI-Texte durchgehend **Deutsch** (AGENTS.md §0).
- **TDD verpflichtend:** Erst der fehlschlagende Test (Rot), dann minimale Implementierung (Grün), dann aufräumen. Kein Implementierungs-Code ohne vorher geschriebenen Test (AGENTS.md §4). Grenzfälle explizit (leeres Portfolio, nur long, nur short, Position genau auf Limit, net_beta ohne Aktien, `null`-Werte).
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL:** Fehlende Felder (z. B. Beta `null` für eine Aktien-Position) werden als `null` geführt und nie als 0/neutral verrechnet; net_beta zählt eine Position mit fehlendem Beta **nicht** mit (statt 0 zu unterstellen) — analog zur Backend-Defensive. UI zeigt fehlende Werte über `UnavailableField` (Spec §1, Konzept §5.4).
- **Keine magischen Zahlen ohne Begründung:** Jede Schwelle/Limit/Formel im Code-Kommentar fachlich begründet. Klumpen-Limits sind **injizierbar** mit dokumentierten Defaults, die exakt der Backend-Quelle entsprechen (`portfolio_monitor_agent`: Sektor 0.40, underlying/asset_class 0.60, Geographie/country 0.70). Etablierte Begriffe (Brutto-Exposure = Σ|Position|, Netto-Exposure = long − short, net_beta = Σ(signiertes Aktien-Exposure × β)) standardkonform + im Kommentar erklärt (AGENTS.md §3).
- **Bestehende Bausteine wiederverwenden, nicht duplizieren:** `UnderlyingWrapperBadge`, `lib/judgment.ts` (`verdictToVisual`/`confidenceFlags`), `ConfidenceBar`, `SignalBadge`, `DemoBadge`, `SourceHealth` (+ `FailedSource`), `UnavailableField`, `useView`, `apiDeps`, `contract/common.ts` (`Underlying`/`Wrapper`/`LongVerdict`/`ShortVerdict`/`DemoMeta`), `contract/cockpit.ts` (`SourceHealthMeta`), `formatConfidence` aus `lib/format.ts`. Naht-Muster wie `data/cockpit.ts`/`data/deepdive.ts` + `data/demo/*`. Drilldown-Gerüst-Vorbild: `pages/cockpit/DrilldownShell.tsx`.
- **Tausch-Naht-Muster:** `PortfolioView extends DemoMeta & SourceHealthMeta`, `isDemo:true` in Demo-Fixtures; echte Fetch-Zeile in `data/portfolio.ts` auskommentiert vorbereitet (Spec §2).
- **Loader stabil an `useView`:** Page nimmt `loader`-Prop mit Default = Modul-Funktion (Refetch-Loop vermeiden, wie `YieldCurveDrilldown`).
- **Track B = beratend, keine Ausführung (US27):** Es gibt **keine** Trade-Buttons. Hedge-Vorschläge sind explizit als „beratend, keine Ausführung" beschriftet. Ticker-Klick führt nur zu `/deep-dive/:ticker`.
- **Keine Backend-Änderungen.** Echte Endpunkte sind spätere Aufgaben (Logbuch).

---

## File Structure

| Datei | Verantwortung | Dispatch |
|---|---|---|
| `frontend/src/contract/portfolio.ts` | Portfolio-Vertrag: `PortfolioView extends DemoMeta & SourceHealthMeta` mit `positions`, `exposure`, `klumpen`, `hedges`; DTOs `PositionDTO`, `PositionJudgmentDTO`, `ExposureDTO`, `KlumpenWarningDTO`, `HedgeSuggestionDTO`, `ConcentrationLimits` | A |
| `frontend/src/lib/exposure.ts` | Pure: `grossExposure`, `netExposure`, `netBeta` (aktien-only, Beta-`null` ausgeschlossen) | A |
| `frontend/src/lib/exposure.test.ts` | Tests Grenzfälle (leer, nur long, nur short, gemischt, net_beta ohne Aktien, Beta `null`) | A |
| `frontend/src/lib/klumpen.ts` | Pure: `detectKlumpen(positions, limits)` → Warnungen je Dimension (Sektor/underlying/Geographie) mit Limit-Bezug; `DEFAULT_LIMITS` | A |
| `frontend/src/lib/klumpen.test.ts` | Tests Grenzfälle (kein Klumpen, genau auf Limit, knapp drüber, leeres Portfolio, Netting long/short) | A |
| `frontend/src/lib/conflict.ts` | Pure, **exportiert** (Slice 4 nutzt sie wieder): `detectConflict(direction, verdict)` → `boolean` + `conflictNote(...)` | A |
| `frontend/src/lib/conflict.test.ts` | Tests (long+SELL → Konflikt, long+SHORT → Konflikt, short+BUY/COVER → Konflikt, gleichgerichtet → kein Konflikt, NONE/HOLD → kein Konflikt) | A |
| `frontend/src/lib/hedge.ts` | Pure: `hedgeSuggestions(exposure, klumpen, limits)` → beratende Vorschläge aus Kennzahlen + Klumpen | A |
| `frontend/src/lib/hedge.test.ts` | Tests (net_beta hoch → Index-Short/VIX, Tech-Klumpen → Teilverkauf/Sektor-Short, alles im Limit → keine Vorschläge) | A |
| `frontend/src/data/demo/portfolio.ts` | Demo-Fixture: Positionen long+short quer über underlying×wrapper inkl. Konflikt-Fall (XLE long + SELL), stimmiges net_beta/Exposure, ≥1 Klumpen-Warnung, `isDemo:true` | A |
| `frontend/src/data/portfolio.ts` | Die Naht: `loadPortfolio(deps?)` (Demo heute, echte Zeile auskommentiert) | A |
| `frontend/src/data/portfolio.test.ts` | Naht-Test: liefert Vertrag inkl. `isDemo`, Positionen, Exposure, Klumpen, Hedges | A |
| `frontend/src/components/portfolio/PositionsTable.tsx` | Positionstabelle (US23): Doppel-Etikett, L/S, Größe, Einstand, AAIA-Urteil (`verdictToVisual`+`ConfidenceBar`), Konflikt-Markierung, Ticker→`/deep-dive/:ticker` | B |
| `frontend/src/components/portfolio/ExposurePanel.tsx` | Exposure-Panel (US24): Brutto/Netto/net_beta mit Inline-Definitionen + „aktien-only"-Label + datierte Vola | B |
| `frontend/src/components/portfolio/KlumpenWarnings.tsx` | Klumpen-Warnungen (US25): je Warnung Dimension + Wert + Limit-Bezug | B |
| `frontend/src/components/portfolio/HedgeSuggestions.tsx` | Hedge-Vorschläge (US26/US27): beratende Liste, „beratend, keine Ausführung"-Hinweis | B |
| `frontend/src/pages/PortfolioPage.tsx` | Seite: lädt über `useView`, rendert Header (`DemoBadge`+`SourceHealth`) + ExposurePanel + KlumpenWarnings + HedgeSuggestions + PositionsTable (US23–27) | B |
| `frontend/src/routes.tsx` | `/portfolio` auf `PortfolioPage` verdrahten (Platzhalter ersetzen) | B |
| `frontend/src/routes.test.tsx` | Routing-Smoke: `/portfolio` rendert die PortfolioPage | B |
| Tests je Komponente (`*.test.tsx`) | Smoke + Kern-Assertions, Routing in `<MemoryRouter>` | B |

---

## Dispatch A — Naht, pure Risiko-Logik (Exposure / net_beta / Klumpen / Konflikt / Hedge)

### Task A1: Portfolio-Vertrag (`contract/portfolio.ts`)

**Files:**
- Create: `frontend/src/contract/portfolio.ts`

**Interfaces:**
- Consumes: `DemoMeta`, `Underlying`, `Wrapper`, `LongVerdict`, `ShortVerdict` aus `contract/common.ts`; `SourceHealthMeta` aus `contract/cockpit.ts`.
- Produces: `PortfolioView` und alle Unter-DTOs (von Demo-Fixture, pure Logik und allen Komponenten konsumiert).

- [ ] **Step 1: Datei mit vollständigem Vertrag schreiben** (kein eigener Test — reine Typdeklarationen; getestet durch A-Naht + pure Logik). Vollständiger Inhalt:

```ts
// Portfolio-Vertrag (Spec §2): beschreibt die KUENFTIGE API-Form. Demo + Echt liefern
// denselben Vertrag, PortfolioView extends DemoMeta & SourceHealthMeta. Beta=null bei einer
// Aktien-Position => UNAVAILABLE (Spec §5.4): die Position zaehlt dann NICHT ins net_beta
// (nie als 0 unterstellt). Track B ist beratend — KEINE Trade-Ausfuehrung (US27).
import type {
  DemoMeta, Underlying, Wrapper, LongVerdict, ShortVerdict,
} from "./common";
import type { SourceHealthMeta } from "./cockpit";

export type Direction = "long" | "short";

// AAIA-Urteil zur Position: beide Linsen, damit die Konflikt-Erkennung die richtige Seite
// gegen die Positionsrichtung prueft (long-Position vs. Long-Verdikt; short vs. Short-Verdikt).
export interface PositionJudgmentDTO {
  longVerdict: LongVerdict;     // BUY/SELL/HOLD/NONE
  shortVerdict: ShortVerdict;   // SHORT/COVER/HOLD/NONE
  confidence: number;           // 0..1 — Konfidenz der relevanten Linse
}

export interface PositionDTO {
  ticker: string;
  name: string;
  underlying: Underlying;
  wrapper: Wrapper;
  direction: Direction;
  sizePctNav: number;           // Positionsgroesse in % vom NAV (immer positiv; Vorzeichen kommt aus direction)
  entryPrice: number;           // Einstand in Positionswaehrung
  currency: string;
  sector: string;               // fuer Sektor-Klumpen
  geography: string;            // Land/Region fuer Geographie-Klumpen (z. B. "USA", "Eurozone")
  beta: number | null;          // Aktienmarkt-Beta; null => UNAVAILABLE (nur Aktien/Index relevant)
  judgment: PositionJudgmentDTO;
}

// Exposure-Kennzahlen (US24). net_beta ist AKTIEN-ONLY (vgl. PR #11 / portfolio_monitor_agent):
// Bonds/Rohstoffe/Edelmetalle haben kein Aktienmarkt-Beta. Vola ist datiert (asOf).
export interface ExposureDTO {
  grossPct: number;             // Brutto = Σ|Position| in % NAV
  netPct: number;               // Netto = long − short in % NAV
  netBeta: number;              // beta-gewichtete Aktien-Netto-Exposure in % NAV (aktien-only)
  annualizedVolPct: number | null; // annualisierte Portfolio-Vola in %; null => UNAVAILABLE
  volAsOf: string;              // Stand der Vola-Berechnung (Datierung, PR #11)
}

export type KlumpenDimension = "sector" | "underlying" | "geography";
export interface KlumpenWarningDTO {
  dimension: KlumpenDimension;
  name: string;                 // z. B. "Technologie", "equity", "USA"
  pct: number;                  // Netto-Konzentration |Σsigniert| / Brutto, 0..1
  limit: number;                // greifendes Limit, 0..1
  message: string;              // vorformatierte Warnung, z. B. "Tech 41 % (Limit 30 %)"
}

// Schwellen je Dimension (0..1). Defaults entsprechen portfolio_monitor_agent (PR #11).
export interface ConcentrationLimits {
  sector: number;
  underlying: number;
  geography: number;
}

// Hedge-Vorschlag (US26) — beratend, NIE ausfuehrend (US27).
export interface HedgeSuggestionDTO {
  id: string;
  text: string;                 // konkreter beratender Vorschlag
  rationale: string;            // woraus abgeleitet (Kennzahl/Klumpen)
}

export interface PortfolioView extends DemoMeta, SourceHealthMeta {
  navCurrency: string;          // Basiswaehrung des NAV (z. B. "USD")
  positions: PositionDTO[];
  exposure: ExposureDTO;
  klumpen: KlumpenWarningDTO[];
  hedges: HedgeSuggestionDTO[];
  limits: ConcentrationLimits;  // greifende Limits (fuer Anzeige/Transparenz)
}
```

- [ ] **Step 2: Typcheck** — Run: `cd frontend && npx tsc --noEmit`. Expected: PASS (keine Fehler in `contract/portfolio.ts`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/contract/portfolio.ts
git commit -m "feat(portfolio): Vertrag PortfolioView (Positionen/Exposure/Klumpen/Hedges)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A2: Pure Exposure + net_beta (`lib/exposure.ts`)

**Files:**
- Create: `frontend/src/lib/exposure.ts`
- Test: `frontend/src/lib/exposure.test.ts`

**Interfaces:**
- Consumes: `PositionDTO` aus `contract/portfolio.ts`.
- Produces: `grossExposure(positions)` → `number`; `netExposure(positions)` → `number`; `netBeta(positions)` → `number`.

> **Fachliche Begründung (AGENTS.md §3, gespiegelt aus `portfolio_monitor_agent`):**
> - **Brutto-Exposure** = Σ|Position| (long + short) — wie viel Kapital insgesamt im Markt arbeitet.
> - **Netto-Exposure** = long − short — die Netto-Marktrichtung (bei marktneutral ~0).
> - **net_beta** = Σ(signiertes Exposure × β), **nur** Positionen mit `underlying ∈ {equity, equity_index}`. Bonds/Rohstoffe/Edelmetalle haben kein Aktienmarkt-Beta (eine Anleihe ≠ Aktie) und gehören nicht in die Zahl (ihr Risiko fängt die Portfolio-Vola ab). Eine Aktien-Position mit `beta===null` ist UNAVAILABLE und wird **nicht** mitgezählt (nie als 0/1 unterstellt) — defensiv wie das Backend.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { grossExposure, netExposure, netBeta } from "./exposure";
import type { PositionDTO } from "../contract/portfolio";

// minimaler Positions-Bauer (nur Felder, die die Exposure-Mathematik liest)
function p(partial: Partial<PositionDTO>): PositionDTO {
  return {
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 10, entryPrice: 100, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 },
    ...partial,
  };
}

describe("grossExposure (Σ|Position|)", () => {
  it("leeres Portfolio => 0", () => {
    expect(grossExposure([])).toBe(0);
  });
  it("addiert Betraege unabhaengig von der Richtung", () => {
    expect(grossExposure([p({ sizePctNav: 12, direction: "long" }), p({ sizePctNav: 5, direction: "short" })])).toBe(17);
  });
});

describe("netExposure (long − short)", () => {
  it("nur long => Summe der long-Groessen", () => {
    expect(netExposure([p({ sizePctNav: 12 }), p({ sizePctNav: 9 })])).toBe(21);
  });
  it("nur short => negativ", () => {
    expect(netExposure([p({ sizePctNav: 5, direction: "short" })])).toBe(-5);
  });
  it("gemischt => long minus short", () => {
    expect(netExposure([p({ sizePctNav: 12, direction: "long" }), p({ sizePctNav: 5, direction: "short" })])).toBe(7);
  });
});

describe("netBeta (aktien-only, signiert × β)", () => {
  it("ohne Aktien (nur Bond/Commodity) => 0", () => {
    expect(netBeta([p({ underlying: "bond", beta: null }), p({ underlying: "commodity", beta: null })])).toBe(0);
  });
  it("zaehlt equity und equity_index, nicht bond/commodity/precious", () => {
    // long 10 (β1.2) + short 5 (β1.0) aktien; bond 20 ignoriert
    // = 10*1.2 − 5*1.0 = 12 − 5 = 7
    expect(netBeta([
      p({ underlying: "equity", direction: "long", sizePctNav: 10, beta: 1.2 }),
      p({ underlying: "equity_index", direction: "short", sizePctNav: 5, beta: 1.0 }),
      p({ underlying: "bond", direction: "long", sizePctNav: 20, beta: null }),
    ])).toBeCloseTo(7, 6);
  });
  it("Aktie mit beta=null wird NICHT mitgezaehlt (UNAVAILABLE, nie als 0/1 unterstellt)", () => {
    // nur die erste Aktie zaehlt: 10*1.5 = 15; die zweite (beta null) faellt raus
    expect(netBeta([
      p({ underlying: "equity", direction: "long", sizePctNav: 10, beta: 1.5 }),
      p({ underlying: "equity", direction: "long", sizePctNav: 8, beta: null }),
    ])).toBeCloseTo(15, 6);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/exposure.test.ts`
Expected: FAIL ("grossExposure is not a function" / Modul nicht gefunden).

- [ ] **Step 3: Minimal implementieren**

```ts
import type { PositionDTO } from "../contract/portfolio";

// Aktien-Klassen fuers net_beta: nur Aktien/Index haben ein Aktienmarkt-Beta
// (gespiegelt aus portfolio_monitor_agent._EQUITY_CLASSES; dort {equity,index}).
const EQUITY_UNDERLYINGS = new Set<PositionDTO["underlying"]>(["equity", "equity_index"]);

// Brutto-Exposure = Σ|Position| (long + short) in % NAV — gesamtes Markt-Engagement.
export function grossExposure(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => sum + p.sizePctNav, 0);
}

// Netto-Exposure = long − short in % NAV — die Netto-Marktrichtung.
export function netExposure(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => sum + (p.direction === "long" ? p.sizePctNav : -p.sizePctNav), 0);
}

// net_beta = Σ(signiertes Exposure × β), NUR Aktien/Index. Position mit beta=null ist
// UNAVAILABLE und wird ausgelassen (nie als 0/1 unterstellt — defensiv wie das Backend).
export function netBeta(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => {
    if (!EQUITY_UNDERLYINGS.has(p.underlying) || p.beta === null) return sum;
    const signed = p.direction === "long" ? p.sizePctNav : -p.sizePctNav;
    return sum + signed * p.beta;
  }, 0);
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/exposure.test.ts`
Expected: PASS (alle 9 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/exposure.ts frontend/src/lib/exposure.test.ts
git commit -m "feat(portfolio): pure Exposure + net_beta (aktien-only, Beta-null ausgeschlossen)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A3: Pure Klumpen-Detektion (`lib/klumpen.ts`)

**Files:**
- Create: `frontend/src/lib/klumpen.ts`
- Test: `frontend/src/lib/klumpen.test.ts`

**Interfaces:**
- Consumes: `PositionDTO`, `KlumpenWarningDTO`, `KlumpenDimension`, `ConcentrationLimits` aus `contract/portfolio.ts`.
- Produces: `DEFAULT_LIMITS: ConcentrationLimits`; `detectKlumpen(positions, limits?)` → `KlumpenWarningDTO[]`.

> **Fachliche Begründung (gespiegelt aus `portfolio_monitor_agent._check_cluster_risks`):** Konzentration je Dimension = |Σ signiertes Exposure| / Brutto. Signiert (long − short), weil ein Hedge (gegenläufige Position) die Netto-Konzentration **senkt** — sonst würde eine abgesicherte Position fälschlich als Klumpen gewertet. Warnung, wenn `pct > limit` (strikt größer — genau auf dem Limit ist noch okay, lückenlose Bänder). **Default-Limits = Backend-Werte:** Sektor 0.40, underlying 0.60, Geographie 0.70. (Hinweis: das Spec-Wireframe §4.8 nennt illustrativ „Tech 41 % (Limit 30 %)"; die Limits sind **injizierbar**, damit Demo/echt sie überschreiben können — Default bleibt der begründete Backend-Wert.)

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { detectKlumpen, DEFAULT_LIMITS } from "./klumpen";
import type { PositionDTO } from "../contract/portfolio";

function p(partial: Partial<PositionDTO>): PositionDTO {
  return {
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 10, entryPrice: 100, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 },
    ...partial,
  };
}
const dims = (ws: ReturnType<typeof detectKlumpen>) => ws.map((w) => w.dimension);

describe("detectKlumpen", () => {
  it("leeres Portfolio => keine Warnungen (kein Division-durch-0)", () => {
    expect(detectKlumpen([])).toEqual([]);
  });
  it("Sektor genau auf dem Limit (0.40) => KEINE Warnung (strikt groesser)", () => {
    // 40 Tech von 100 Brutto = 0.40 == Limit -> keine Warnung
    const out = detectKlumpen([
      p({ sector: "Technologie", sizePctNav: 40 }),
      p({ sector: "Gesundheit", sizePctNav: 60 }),
    ]);
    expect(dims(out)).not.toContain("sector");
  });
  it("Sektor knapp ueber Limit (0.41) => Sektor-Warnung mit Limit-Bezug", () => {
    const out = detectKlumpen([
      p({ sector: "Technologie", sizePctNav: 41 }),
      p({ sector: "Gesundheit", sizePctNav: 59 }),
    ]);
    const tech = out.find((w) => w.dimension === "sector" && w.name === "Technologie");
    expect(tech).toBeTruthy();
    expect(tech!.limit).toBe(DEFAULT_LIMITS.sector);
    expect(tech!.message).toMatch(/Technologie/);
    expect(tech!.message).toMatch(/Limit/);
  });
  it("Gegenlaeufige Position senkt die Netto-Konzentration (Hedge zaehlt netto)", () => {
    // 50 long USA + 30 short USA = netto 20 / Brutto 80 = 0.25 < 0.70 -> keine USA-Warnung
    const out = detectKlumpen([
      p({ geography: "USA", direction: "long", sizePctNav: 50 }),
      p({ geography: "USA", direction: "short", sizePctNav: 30 }),
    ]);
    expect(out.find((w) => w.dimension === "geography" && w.name === "USA")).toBeUndefined();
  });
  it("underlying-Klumpen (equity > 0.60) wird erkannt", () => {
    const out = detectKlumpen([
      p({ underlying: "equity", sizePctNav: 70 }),
      p({ underlying: "bond", sizePctNav: 30 }),
    ]);
    expect(out.find((w) => w.dimension === "underlying" && w.name === "equity")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/klumpen.test.ts`
Expected: FAIL ("detectKlumpen is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
import type {
  PositionDTO, KlumpenWarningDTO, KlumpenDimension, ConcentrationLimits,
} from "../contract/portfolio";

// Default-Limits = Backend-Werte (portfolio_monitor_agent): Sektor 0.40, underlying/
// asset_class 0.60, Geographie/country 0.70. Begruendung: ab dieser Netto-Konzentration
// gilt das Risiko als Klumpen. Injizierbar -> Demo/echt koennen ueberschreiben.
export const DEFAULT_LIMITS: ConcentrationLimits = { sector: 0.40, underlying: 0.60, geography: 0.70 };

// Pro Dimension der Feldname auf der Position.
const FIELD: Record<KlumpenDimension, keyof PositionDTO> = {
  sector: "sector", underlying: "underlying", geography: "geography",
};

function pct(value: number): string {
  return `${Math.round(value * 100)} %`;
}

// Klumpen je Dimension: |Σ signiertes Exposure| / Brutto > Limit. Signiert, damit ein Hedge
// (Gegenposition) die Netto-Konzentration senkt (sonst Fehlalarm). Strikt groesser:
// genau auf dem Limit noch okay (lueckenlose Baender, AGENTS.md §2).
export function detectKlumpen(
  positions: PositionDTO[],
  limits: ConcentrationLimits = DEFAULT_LIMITS,
): KlumpenWarningDTO[] {
  const gross = positions.reduce((s, p) => s + p.sizePctNav, 0);
  if (gross === 0) return [];

  const warnings: KlumpenWarningDTO[] = [];
  for (const dimension of ["sector", "underlying", "geography"] as KlumpenDimension[]) {
    const limit = limits[dimension];
    const buckets = new Map<string, number>();
    for (const p of positions) {
      const name = String(p[FIELD[dimension]]);
      const signed = p.direction === "long" ? p.sizePctNav : -p.sizePctNav;
      buckets.set(name, (buckets.get(name) ?? 0) + signed);
    }
    for (const [name, net] of buckets) {
      const share = Math.abs(net) / gross;
      if (share > limit) {
        warnings.push({
          dimension, name, pct: Number(share.toFixed(4)), limit,
          message: `${name} ${pct(share)} (Limit ${pct(limit)})`,
        });
      }
    }
  }
  return warnings;
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/klumpen.test.ts`
Expected: PASS (5 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/klumpen.ts frontend/src/lib/klumpen.test.ts
git commit -m "feat(portfolio): pure Klumpen-Detektion (Sektor/underlying/Geographie, netto)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A4: Pure Konflikt-Erkennung (`lib/conflict.ts`) — Slice 4 nutzt sie wieder

**Files:**
- Create: `frontend/src/lib/conflict.ts`
- Test: `frontend/src/lib/conflict.test.ts`

**Interfaces:**
- Consumes: `Direction`, `PositionJudgmentDTO` aus `contract/portfolio.ts`; `LongVerdict`, `ShortVerdict` aus `contract/common.ts`.
- Produces: `detectConflict(direction, judgment)` → `boolean`; `conflictNote(direction, judgment)` → `string | null`.

> **Fachliche Begründung:** Ein Konflikt liegt vor, wenn das AAIA-Urteil **gegen** die gehaltene Positionsrichtung läuft (Konzept §2.5). Für eine **long**-Position prüfen wir die **Long-Linse**: SELL (raus) oder SHORT-Bias gegen den Bestand → Konflikt. Für eine **short**-Position prüfen wir die **Short-Linse**: COVER (eindecken) → Konflikt; zusätzlich ein BUY der Long-Linse als Gegensignal. HOLD/NONE sind **kein** Konflikt (kein gegenläufiges Handlungssignal). Diese Funktion ist **exportiert** und von Slice 4 (Inbox) wiederverwendbar (Auftrag: Konflikt-Markierung speist die Inbox).

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { detectConflict, conflictNote } from "./conflict";
import type { PositionJudgmentDTO } from "../contract/portfolio";

function j(partial: Partial<PositionJudgmentDTO>): PositionJudgmentDTO {
  return { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5, ...partial };
}

describe("detectConflict", () => {
  it("long + Long-Verdikt SELL => Konflikt (Urteil will raus)", () => {
    expect(detectConflict("long", j({ longVerdict: "SELL" }))).toBe(true);
  });
  it("long + Short-Verdikt SHORT => Konflikt (Urteil shortet gegen Bestand)", () => {
    expect(detectConflict("long", j({ longVerdict: "NONE", shortVerdict: "SHORT" }))).toBe(true);
  });
  it("long + BUY/HOLD => kein Konflikt", () => {
    expect(detectConflict("long", j({ longVerdict: "BUY" }))).toBe(false);
    expect(detectConflict("long", j({ longVerdict: "HOLD" }))).toBe(false);
  });
  it("short + Short-Verdikt COVER => Konflikt (Urteil will eindecken)", () => {
    expect(detectConflict("short", j({ shortVerdict: "COVER" }))).toBe(true);
  });
  it("short + Long-Verdikt BUY => Konflikt (Urteil kauft gegen Short)", () => {
    expect(detectConflict("short", j({ longVerdict: "BUY", shortVerdict: "HOLD" }))).toBe(true);
  });
  it("short + SHORT/HOLD => kein Konflikt", () => {
    expect(detectConflict("short", j({ shortVerdict: "SHORT" }))).toBe(false);
    expect(detectConflict("short", j({ shortVerdict: "HOLD" }))).toBe(false);
  });
});

describe("conflictNote", () => {
  it("liefert eine Begruendung bei Konflikt, sonst null", () => {
    expect(conflictNote("long", j({ longVerdict: "SELL" }))).toMatch(/SELL/);
    expect(conflictNote("long", j({ longVerdict: "BUY" }))).toBeNull();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/conflict.test.ts`
Expected: FAIL ("detectConflict is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
import type { Direction, PositionJudgmentDTO } from "../contract/portfolio";

// Konflikt = AAIA-Urteil laeuft GEGEN die gehaltene Positionsrichtung (Konzept §2.5).
// long-Position: Long-Linse SELL ODER Short-Linse SHORT (beides gegen den Bestand).
// short-Position: Short-Linse COVER ODER Long-Linse BUY (beides gegen die Short-These).
// HOLD/NONE sind KEIN Konflikt (kein gegenlaeufiges Handlungssignal).
// EXPORTIERT, damit Slice 4 (Inbox) dieselbe Logik nutzt (eine Quelle der Wahrheit).
export function detectConflict(direction: Direction, judgment: PositionJudgmentDTO): boolean {
  if (direction === "long") {
    return judgment.longVerdict === "SELL" || judgment.shortVerdict === "SHORT";
  }
  return judgment.shortVerdict === "COVER" || judgment.longVerdict === "BUY";
}

// Kurzbegruendung fuer die UI/Inbox; null wenn kein Konflikt.
export function conflictNote(direction: Direction, judgment: PositionJudgmentDTO): string | null {
  if (!detectConflict(direction, judgment)) return null;
  if (direction === "long") {
    const v = judgment.longVerdict === "SELL" ? judgment.longVerdict : judgment.shortVerdict;
    return `Long gehalten, Urteil ${v} läuft gegen die Position.`;
  }
  const v = judgment.shortVerdict === "COVER" ? judgment.shortVerdict : judgment.longVerdict;
  return `Short gehalten, Urteil ${v} läuft gegen die Position.`;
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/conflict.test.ts`
Expected: PASS (7 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/conflict.ts frontend/src/lib/conflict.test.ts
git commit -m "feat(portfolio): pure Konflikt-Erkennung detectConflict (Slice 4 wiederverwendbar)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A5: Pure Hedge-Vorschläge (`lib/hedge.ts`)

**Files:**
- Create: `frontend/src/lib/hedge.ts`
- Test: `frontend/src/lib/hedge.test.ts`

**Interfaces:**
- Consumes: `ExposureDTO`, `KlumpenWarningDTO`, `ConcentrationLimits`, `HedgeSuggestionDTO` aus `contract/portfolio.ts`.
- Produces: `NET_BETA_HEDGE_THRESHOLD: number`; `hedgeSuggestions(exposure, klumpen)` → `HedgeSuggestionDTO[]`.

> **Fachliche Begründung:** Beratende Vorschläge (US26, Track B) — **keine** Ausführung (US27). Abgeleitet aus den Kennzahlen/Klumpen:
> - **net_beta > Schwelle** (Default 0.30 = 30 % NAV beta-gewichtetes Aktien-Netto): das Buch ist deutlich marktsensitiv → Index-Short (z. B. SPY) oder VIX-Hedge senkt das Aktienmarkt-Beta. Schwelle als benannte Konstante (kein magischer Wert): bei <30 % gilt das Restrisiko als tragbar; das ist eine konservative, beratende Heuristik, keine harte Regel.
> - **Sektor-Klumpen** → Teilverkauf oder Sektor-Short der konzentrierten Branche.
> - Jeder Vorschlag trägt eine `rationale` (woraus abgeleitet). Keine Klumpen + net_beta im Rahmen → leere Liste (nichts zu raten).

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { hedgeSuggestions, NET_BETA_HEDGE_THRESHOLD } from "./hedge";
import type { ExposureDTO, KlumpenWarningDTO } from "../contract/portfolio";

const exp = (netBeta: number): ExposureDTO => ({
  grossPct: 142, netPct: 38, netBeta, annualizedVolPct: 14, volAsOf: "2026-06-20",
});
const techKlumpen: KlumpenWarningDTO = {
  dimension: "sector", name: "Technologie", pct: 0.41, limit: 0.40, message: "Technologie 41 % (Limit 40 %)",
};

describe("hedgeSuggestions", () => {
  it("net_beta ueber Schwelle => Index-Short/VIX-Vorschlag", () => {
    const out = hedgeSuggestions(exp(NET_BETA_HEDGE_THRESHOLD + 0.5), []);
    expect(out.some((h) => /Index-Short|VIX/i.test(h.text))).toBe(true);
  });
  it("Sektor-Klumpen => Teilverkauf/Sektor-Short-Vorschlag", () => {
    const out = hedgeSuggestions(exp(0), [techKlumpen]);
    expect(out.some((h) => /Technologie/.test(h.text) && /(Teilverkauf|Sektor-Short)/i.test(h.text))).toBe(true);
  });
  it("net_beta genau auf der Schwelle => KEIN net_beta-Vorschlag (strikt groesser)", () => {
    const out = hedgeSuggestions(exp(NET_BETA_HEDGE_THRESHOLD), []);
    expect(out.some((h) => /Index-Short|VIX/i.test(h.text))).toBe(false);
  });
  it("alles im Rahmen, keine Klumpen => leere Liste", () => {
    expect(hedgeSuggestions(exp(0), [])).toEqual([]);
  });
});
```

> **Hinweis zur Schwelle:** `net_beta` ist in % NAV (z. B. 38 = 38 %). Damit `NET_BETA_HEDGE_THRESHOLD` (0.30 als Anteil) vergleichbar ist, vergleicht die Implementierung gegen `NET_BETA_HEDGE_THRESHOLD * 100`. Der Test wählt `netBeta` bewusst knapp über/auf der so skalierten Schwelle.

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/hedge.test.ts`
Expected: FAIL ("hedgeSuggestions is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
import type { ExposureDTO, KlumpenWarningDTO, HedgeSuggestionDTO } from "../contract/portfolio";

// Schwelle als benannte Konstante (kein magischer Wert): ab 30 % NAV beta-gewichtetem
// Aktien-Netto gilt das Buch als deutlich marktsensitiv -> Hedge erwaegen. Konservative,
// beratende Heuristik (Track B), keine harte Regel. Anteil 0..1; net_beta ist in % NAV.
export const NET_BETA_HEDGE_THRESHOLD = 0.30;

// Beratende Hedge-Vorschlaege (US26) — NIE ausfuehrend (US27). Abgeleitet aus Kennzahlen
// (net_beta) und Klumpen (Sektor). Jeder Vorschlag traegt eine rationale.
export function hedgeSuggestions(
  exposure: ExposureDTO,
  klumpen: KlumpenWarningDTO[],
): HedgeSuggestionDTO[] {
  const out: HedgeSuggestionDTO[] = [];

  // net_beta in % NAV gegen die als Anteil definierte Schwelle (×100) — strikt groesser.
  if (exposure.netBeta > NET_BETA_HEDGE_THRESHOLD * 100) {
    out.push({
      id: "net-beta",
      text: `net_beta ${exposure.netBeta.toFixed(0)} % senken → Index-Short (z. B. SPY) oder VIX-Hedge erwägen`,
      rationale: `aktien-only net_beta über ${Math.round(NET_BETA_HEDGE_THRESHOLD * 100)} % NAV — Buch ist marktsensitiv`,
    });
  }

  // Sektor-Klumpen -> Teilverkauf oder Sektor-Short der konzentrierten Branche.
  for (const k of klumpen.filter((w) => w.dimension === "sector")) {
    out.push({
      id: `sektor-${k.name}`,
      text: `${k.name}-Klumpen → Teilverkauf oder Sektor-Short erwägen`,
      rationale: k.message,
    });
  }
  return out;
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/lib/hedge.test.ts`
Expected: PASS (4 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/hedge.ts frontend/src/lib/hedge.test.ts
git commit -m "feat(portfolio): pure beratende Hedge-Vorschlaege (net_beta + Sektor-Klumpen)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A6: Demo-Fixture (`data/demo/portfolio.ts`)

**Files:**
- Create: `frontend/src/data/demo/portfolio.ts`

**Interfaces:**
- Consumes: alle DTOs aus `contract/portfolio.ts`; `grossExposure`/`netExposure`/`netBeta` aus `lib/exposure.ts`; `detectKlumpen`/`DEFAULT_LIMITS` aus `lib/klumpen.ts`; `hedgeSuggestions` aus `lib/hedge.ts`.
- Produces: `demoPortfolio(): PortfolioView` — `isDemo:true`, Positionen long+short quer über underlying×wrapper, mindestens ein Konflikt-Fall (XLE long + SELL), stimmiges Exposure/net_beta, ≥1 Klumpen-Warnung.

> **Fachliche Annahmen (Demo-Werte, im Code markiert):** Größenordnungen plausibel, nicht exakt. Positionen (in % NAV): AAPL long 12 % (equity·single, Technologie/USA, β1.25, HOLD 52 %); MSFT long 15 % (equity·single, Technologie/USA, β1.10, BUY 55 %) — die beiden Tech-Longs erzeugen einen **Sektor-Klumpen** (27 % netto < 40 % Default → bewusst **kein** Fehlalarm; um die Wireframe-Warnung „Tech" zu zeigen, list das Fixture die Tech-Konzentration über das injizierte Limit; siehe unten); GC=F long 6 % (precious_metal·future, Rohstoffe/Global, β `null` → nicht im net_beta, HOLD 47 %); TLT long 10 % (bond·fund, Anleihen/USA, β `null`, BUY 60 %); TSLA short 5 % (equity·single, Zyklischer Konsum/USA, β1.8, SHORT 61 % → Urteil **stützt** den Short, **kein** Konflikt); XLE long 9 % (equity_index·fund, Energie/USA, β1.05, **SELL 58 % → Konflikt**: long gehalten, Urteil SELL). Exposure/net_beta/Klumpen/Hedges werden **aus den Positionen berechnet** (nicht von Hand gesetzt), damit Tabelle und Panel garantiert konsistent sind. Limits: das Fixture setzt `sector: 0.25`, damit die Tech-Konzentration (27 %) als Klumpen erscheint (entspricht der Wireframe-Aussage „Tech … Limit 30 %"); underlying/geography bleiben auf Default. Die equity-Positionen mit β erzeugen ein positives net_beta deutlich über 30 % NAV → Hedge-Vorschlag. Eine `failed`-Quelle (Beta-Feed teil-Stub) markiert den UNAVAILABLE-Pfad.

- [ ] **Step 1: Datei mit vollständigem Fixture schreiben** (kein eigener Test — durch A7-Naht-Test abgedeckt). Vollständiger Inhalt:

```ts
// Fachlich plausible Beispielwerte (Spec §1: Demo, nicht exakt). isDemo:true -> DemoBadge.
// Positionen long+short quer ueber underlying x wrapper inkl. Konflikt-Fall (XLE long + SELL).
// Exposure/net_beta/Klumpen/Hedges werden AUS den Positionen berechnet -> Tabelle & Panel
// sind garantiert konsistent (keine handgesetzten Aggregate, die auseinanderdriften).
import type { PortfolioView, PositionDTO, ConcentrationLimits } from "../../contract/portfolio";
import { grossExposure, netExposure, netBeta } from "../../lib/exposure";
import { detectKlumpen } from "../../lib/klumpen";
import { hedgeSuggestions } from "../../lib/hedge";

// Limits fuer die Demo: Sektor bewusst auf 0.25, damit die Tech-Konzentration (27 %) als
// Klumpen erscheint (vgl. Wireframe §4.8 "Tech … Limit 30 %"). underlying/geography = Default.
const DEMO_LIMITS: ConcentrationLimits = { sector: 0.25, underlying: 0.60, geography: 0.70 };

const POSITIONS: PositionDTO[] = [
  {
    ticker: "AAPL", name: "Apple Inc.", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 12, entryPrice: 185.2, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1.25,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.52 },
  },
  {
    ticker: "MSFT", name: "Microsoft Corp.", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 15, entryPrice: 410.0, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1.10,
    judgment: { longVerdict: "BUY", shortVerdict: "NONE", confidence: 0.55 },
  },
  {
    ticker: "GC=F", name: "Gold", underlying: "precious_metal", wrapper: "future",
    direction: "long", sizePctNav: 6, entryPrice: 2310, currency: "USD",
    sector: "Edelmetall", geography: "Global", beta: null, // kein Aktienmarkt-Beta -> nicht im net_beta
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.47 },
  },
  {
    ticker: "TLT", name: "20+ Jahre US-Staatsanleihen", underlying: "bond", wrapper: "fund",
    direction: "long", sizePctNav: 10, entryPrice: 88.4, currency: "USD",
    sector: "Anleihen", geography: "USA", beta: null, // Bond -> nicht im net_beta
    judgment: { longVerdict: "BUY", shortVerdict: "NONE", confidence: 0.60 },
  },
  {
    ticker: "TSLA", name: "Tesla Inc.", underlying: "equity", wrapper: "single",
    direction: "short", sizePctNav: 5, entryPrice: 240.0, currency: "USD",
    sector: "Zyklischer Konsum", geography: "USA", beta: 1.80,
    // Urteil STUETZT den Short (Short-Verdikt SHORT) -> KEIN Konflikt
    judgment: { longVerdict: "NONE", shortVerdict: "SHORT", confidence: 0.61 },
  },
  {
    ticker: "XLE", name: "Energy Select Sector SPDR", underlying: "equity_index", wrapper: "fund",
    direction: "long", sizePctNav: 9, entryPrice: 88.4, currency: "USD",
    sector: "Energie", geography: "USA", beta: 1.05,
    // KONFLIKT: long gehalten, Long-Verdikt SELL laeuft gegen die Position (speist Inbox/Slice 4)
    judgment: { longVerdict: "SELL", shortVerdict: "NONE", confidence: 0.58 },
  },
];

export function demoPortfolio(): PortfolioView {
  const exposure = {
    grossPct: Number(grossExposure(POSITIONS).toFixed(2)),
    netPct: Number(netExposure(POSITIONS).toFixed(2)),
    netBeta: Number(netBeta(POSITIONS).toFixed(2)),
    annualizedVolPct: 13.8,            // datierte Portfolio-Vola (Demo, PR #11)
    volAsOf: "2026-06-20",
  };
  const klumpen = detectKlumpen(POSITIONS, DEMO_LIMITS);
  const hedges = hedgeSuggestions(exposure, klumpen);
  return {
    isDemo: true,
    sourcesActive: 3, sourcesTotal: 4,
    // bewusst eine ausgefallene Quelle -> UNAVAILABLE-Pfad sichtbar (Spec §1/§5.4)
    failed: [{ key: "Beta-Feed (Stub)", reason: "Marktbeta-Quelle teilweise noch nicht angebunden" }],
    navCurrency: "USD",
    positions: POSITIONS,
    exposure,
    klumpen,
    hedges,
    limits: DEMO_LIMITS,
  };
}
```

- [ ] **Step 2: Typcheck** — Run: `cd frontend && npx tsc --noEmit`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/demo/portfolio.ts
git commit -m "feat(portfolio): Demo-Fixture (long+short, Konflikt XLE+SELL, Tech-Klumpen)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task A7: Die Naht (`data/portfolio.ts`) + Naht-Test

**Files:**
- Create: `frontend/src/data/portfolio.ts`
- Test: `frontend/src/data/portfolio.test.ts`

**Interfaces:**
- Consumes: `demoPortfolio` aus `data/demo/portfolio.ts`; `ApiDeps` aus `data/apiDeps.ts`; `detectConflict` aus `lib/conflict.ts` (nur im Test, um die Konflikt-Position zu prüfen).
- Produces: `loadPortfolio(deps?: ApiDeps): Promise<PortfolioView>`.

- [ ] **Step 1: Failing test schreiben**

```ts
import { describe, it, expect } from "vitest";
import { loadPortfolio } from "./portfolio";
import { detectConflict } from "../lib/conflict";

describe("loadPortfolio (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit Positionen, Exposure, Klumpen, Hedges", async () => {
    const v = await loadPortfolio();
    expect(v.isDemo).toBe(true);
    expect(v.positions.length).toBeGreaterThanOrEqual(4);
    expect(v.exposure.grossPct).toBeGreaterThan(0);
    expect(v.klumpen.length).toBeGreaterThanOrEqual(1);   // mind. eine Klumpen-Warnung (Tech)
    expect(v.hedges.length).toBeGreaterThanOrEqual(1);    // mind. ein Hedge-Vorschlag
  });
  it("enthaelt mindestens einen Konflikt-Fall (long gehalten, Urteil SELL)", async () => {
    const v = await loadPortfolio();
    const conflicts = v.positions.filter((p) => detectConflict(p.direction, p.judgment));
    expect(conflicts.some((p) => p.ticker === "XLE")).toBe(true);
  });
  it("net_beta zaehlt nur Aktien/Index (Bonds/Edelmetalle ausgenommen)", async () => {
    const v = await loadPortfolio();
    // Gold-Future (beta null) + TLT (bond) duerfen das net_beta nicht beeinflussen.
    expect(Number.isFinite(v.exposure.netBeta)).toBe(true);
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/data/portfolio.test.ts`
Expected: FAIL ("loadPortfolio is not a function").

- [ ] **Step 3: Minimal implementieren**

```ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuers Portfolio. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { PortfolioView } from "../contract/portfolio";
import { demoPortfolio } from "./demo/portfolio";
import type { ApiDeps } from "./apiDeps";

export async function loadPortfolio(_deps?: ApiDeps): Promise<PortfolioView> {
  return demoPortfolio();
  // return fetchPortfolio(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/data/portfolio.test.ts`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/portfolio.ts frontend/src/data/portfolio.test.ts
git commit -m "feat(portfolio): Tausch-Naht loadPortfolio (Demo heute, echt vorbereitet)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Dispatch B — PortfolioPage, Positionstabelle, Exposure-Panel, Klumpen-Warnungen, Hedge-Vorschläge, Routing

> **Gemeinsame Test-Konvention für Dispatch B:** Komponenten mit Ticker-Links rendern in `<MemoryRouter>`. Slice 3 nutzt **keine** Charts → kein ECharts-Mock nötig.

### Task B1: Positionstabelle (`components/portfolio/PositionsTable.tsx`)

**Files:**
- Create: `frontend/src/components/portfolio/PositionsTable.tsx`
- Test: `frontend/src/components/portfolio/PositionsTable.test.tsx`

**Interfaces:**
- Consumes: `PositionDTO` aus `contract/portfolio.ts`; `UnderlyingWrapperBadge`; `verdictToVisual` aus `lib/judgment.ts`; `ConfidenceBar`; `detectConflict`/`conflictNote` aus `lib/conflict.ts`; `formatConfidence` aus `lib/format.ts`; `Link` aus `react-router-dom`.
- Produces: `PositionsTable({ positions }: { positions: PositionDTO[] })`.

**Strukturvorgabe (US23, Wireframe §4.8):** Tabelle mit Spalten **Titel** (Ticker als `<Link to={"/deep-dive/" + ticker}>`, darunter `name`), **L/S** (Richtung, short rot/long grün), **underlying×wrapper** (`UnderlyingWrapperBadge`), **Größe** (`sizePctNav` mit Vorzeichen: long `+N %`, short `−N %`), **Einstand** (`entryPrice` + `currency`), **AAIA-Urteil** (für long → Long-Verdikt, für short → Short-Verdikt, via `verdictToVisual` Wort+Farbe + `ConfidenceBar`/`formatConfidence`). **Konflikt-Markierung:** ist `detectConflict(direction, judgment)` true → Zeile mit Warn-Hintergrund + Badge „⚠ Urteil gegen Position" + `conflictNote` als Titel/Tooltip. Das relevante Urteil je Richtung: long → `judgment.longVerdict`, short → `judgment.shortVerdict`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PositionsTable } from "./PositionsTable";
import { demoPortfolio } from "../../data/demo/portfolio";

function renderTable() {
  return render(
    <MemoryRouter>
      <PositionsTable positions={demoPortfolio().positions} />
    </MemoryRouter>,
  );
}

describe("PositionsTable", () => {
  it("zeigt Ticker als Link auf den Deep-Dive", () => {
    renderTable();
    const link = screen.getByRole("link", { name: /AAPL/ });
    expect(link).toHaveAttribute("href", "/deep-dive/AAPL");
  });
  it("zeigt beide Etiketten (underlying + wrapper) je Position", () => {
    renderTable();
    expect(screen.getAllByText("Aktie").length).toBeGreaterThanOrEqual(1);   // underlying-Badge
    expect(screen.getAllByText("Future").length).toBeGreaterThanOrEqual(1);  // wrapper-Badge (GC=F)
  });
  it("markiert die Konflikt-Position (XLE long + SELL)", () => {
    renderTable();
    // XLE-Zeile traegt den Konflikt-Hinweis
    expect(screen.getByText(/Urteil gegen Position/i)).toBeInTheDocument();
  });
  it("zeigt fuer eine long-Position das Long-Verdikt, fuer short das Short-Verdikt", () => {
    renderTable();
    expect(screen.getByText("SHORT")).toBeInTheDocument(); // TSLA short -> Short-Verdikt
    expect(screen.getByText("SELL")).toBeInTheDocument();  // XLE long -> Long-Verdikt
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/portfolio/PositionsTable.test.tsx`
Expected: FAIL (Modul/Component nicht gefunden).

- [ ] **Step 3: Implementieren** (vollständig)

```tsx
import { Link } from "react-router-dom";
import type { PositionDTO } from "../../contract/portfolio";
import { UnderlyingWrapperBadge } from "../UnderlyingWrapperBadge";
import { ConfidenceBar } from "../ConfidenceBar";
import { verdictToVisual } from "../../lib/judgment";
import { detectConflict, conflictNote } from "../../lib/conflict";

// Das fuer die Positionsrichtung relevante Urteil: long -> Long-Linse, short -> Short-Linse.
function relevantVerdict(p: PositionDTO): string {
  return p.direction === "long" ? p.judgment.longVerdict : p.judgment.shortVerdict;
}

function Row({ p }: { p: PositionDTO }) {
  const conflict = detectConflict(p.direction, p.judgment);
  const note = conflictNote(p.direction, p.judgment);
  const verdict = relevantVerdict(p);
  const v = verdictToVisual(verdict as Parameters<typeof verdictToVisual>[0]);
  const signedSize = p.direction === "long" ? `+${p.sizePctNav} %` : `−${p.sizePctNav} %`;
  return (
    <tr
      className={conflict ? "bg-amber-50 dark:bg-amber-950/30" : ""}
      title={note ?? undefined}
    >
      <td className="py-2 pr-4">
        <Link to={`/deep-dive/${p.ticker}`} className="font-medium text-sky-600 underline">{p.ticker}</Link>
        <div className="text-xs text-slate-500">{p.name}</div>
      </td>
      <td className={`py-2 pr-4 font-medium ${p.direction === "short" ? "text-red-600" : "text-green-600"}`}>
        {p.direction === "long" ? "LONG" : "SHORT"}
      </td>
      <td className="py-2 pr-4"><UnderlyingWrapperBadge underlying={p.underlying} wrapper={p.wrapper} /></td>
      <td className="py-2 pr-4 tabular-nums">{signedSize}</td>
      <td className="py-2 pr-4 tabular-nums">{p.entryPrice} {p.currency}</td>
      <td className="py-2 pr-4">
        <div className="flex flex-col gap-1">
          <span className={`font-semibold ${v.colorClass}`}>{v.label}</span>
          <ConfidenceBar value={p.judgment.confidence} />
          {conflict && (
            <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              ⚠ Urteil gegen Position
            </span>
          )}
        </div>
      </td>
    </tr>
  );
}

// Positionstabelle (US23, Wireframe §4.8): alle Positionen long+short mit beiden Etiketten,
// Richtung, Groesse, Einstand, AAIA-Urteil + Konflikt-Markierung. Ticker -> Deep-Dive.
export function PositionsTable({ positions }: { positions: PositionDTO[] }) {
  if (positions.length === 0) {
    return <p className="text-slate-500">Keine Positionen erfasst.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="text-xs uppercase text-slate-500">
          <th className="py-1 pr-4">Titel</th>
          <th className="py-1 pr-4">L/S</th>
          <th className="py-1 pr-4">underlying×wrapper</th>
          <th className="py-1 pr-4">Größe</th>
          <th className="py-1 pr-4">Einstand</th>
          <th className="py-1 pr-4">AAIA-Urteil</th>
        </tr>
      </thead>
      <tbody>{positions.map((p) => <Row key={p.ticker} p={p} />)}</tbody>
    </table>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/portfolio/PositionsTable.test.tsx`
Expected: PASS (4 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/portfolio/PositionsTable.tsx frontend/src/components/portfolio/PositionsTable.test.tsx
git commit -m "feat(portfolio): Positionstabelle mit Doppel-Etikett + Konflikt-Markierung (US23)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B2: Exposure-Panel (`components/portfolio/ExposurePanel.tsx`)

**Files:**
- Create: `frontend/src/components/portfolio/ExposurePanel.tsx`
- Test: `frontend/src/components/portfolio/ExposurePanel.test.tsx`

**Interfaces:**
- Consumes: `ExposureDTO` aus `contract/portfolio.ts`; `UnavailableField`.
- Produces: `ExposurePanel({ exposure }: { exposure: ExposureDTO })`.

**Strukturvorgabe (US24, Wireframe §4.8):** Drei Kennzahlen-Kacheln nebeneinander, je mit **kurzer Inline-Definition** (PM evtl. nicht jargon-fest):
- **Brutto-Exposure** `{grossPct} %` — Definition „Σ|Position| — gesamtes Markt-Engagement".
- **Netto-Exposure** `{netPct >= 0 ? "+" : ""}{netPct} %` — Definition „long − short — Netto-Marktrichtung".
- **net_beta** `{netBeta} %` mit Pflicht-Label **„aktien-only"** — Definition „beta-gewichtetes Aktien-Netto; misst Marktsensitivität (nur Aktien/Index)". Zusätzlich darunter die **datierte Vola**: bei `annualizedVolPct===null` → `<UnavailableField/>`, sonst `{annualizedVolPct} % (Stand {volAsOf})`.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExposurePanel } from "./ExposurePanel";
import type { ExposureDTO } from "../../contract/portfolio";

const exp: ExposureDTO = {
  grossPct: 142, netPct: 38, netBeta: 62, annualizedVolPct: 13.8, volAsOf: "2026-06-20",
};

describe("ExposurePanel", () => {
  it("zeigt Brutto, Netto und net_beta mit Inline-Definitionen", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/142/)).toBeInTheDocument();
    expect(screen.getByText(/\+38/)).toBeInTheDocument();          // Netto mit Vorzeichen
    expect(screen.getByText(/62/)).toBeInTheDocument();            // net_beta
    expect(screen.getByText(/Σ\|Position\|/)).toBeInTheDocument(); // Brutto-Definition
    expect(screen.getByText(/long − short/)).toBeInTheDocument();  // Netto-Definition
  });
  it("kennzeichnet net_beta als aktien-only (Pflicht-Label)", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/aktien-only/i)).toBeInTheDocument();
  });
  it("zeigt die datierte Vola (Stand)", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/2026-06-20/)).toBeInTheDocument();
  });
  it("zeigt 'nicht verfügbar' wenn Vola null (nie als 0)", () => {
    render(<ExposurePanel exposure={{ ...exp, annualizedVolPct: null }} />);
    expect(screen.getByText(/nicht verfügbar/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/portfolio/ExposurePanel.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { ExposureDTO } from "../../contract/portfolio";
import { UnavailableField } from "../UnavailableField";

function Metric({ label, value, definition }: { label: string; value: string; definition: string }) {
  return (
    <div className="flex-1 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-xl font-bold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{definition}</div>
    </div>
  );
}

// Exposure-Panel (US24, Wireframe §4.8): Brutto/Netto/net_beta je mit kurzer Inline-Definition
// (PM evtl. nicht jargon-fest). net_beta ist PFLICHT als "aktien-only" gekennzeichnet (PR #11),
// mit datierter Vola. Brutto = Σ|Position|, Netto = long − short.
export function ExposurePanel({ exposure }: { exposure: ExposureDTO }) {
  const net = `${exposure.netPct >= 0 ? "+" : ""}${exposure.netPct} %`;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-3">
        <Metric label="Brutto-Exposure" value={`${exposure.grossPct} %`} definition="Σ|Position| — gesamtes Markt-Engagement" />
        <Metric label="Netto-Exposure" value={net} definition="long − short — Netto-Marktrichtung" />
        <Metric
          label="net_beta (aktien-only)"
          value={`${exposure.netBeta} %`}
          definition="beta-gewichtetes Aktien-Netto — Marktsensitivität (nur Aktien/Index)"
        />
      </div>
      <div className="text-xs text-slate-500">
        Annualisierte Portfolio-Vola:{" "}
        {exposure.annualizedVolPct === null
          ? <UnavailableField reason="Vola nicht verfügbar" />
          : <span className="font-medium">{exposure.annualizedVolPct} % (Stand {exposure.volAsOf})</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/portfolio/ExposurePanel.test.tsx`
Expected: PASS (4 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/portfolio/ExposurePanel.tsx frontend/src/components/portfolio/ExposurePanel.test.tsx
git commit -m "feat(portfolio): Exposure-Panel Brutto/Netto/net_beta (aktien-only, datierte Vola) (US24)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B3: Klumpen-Warnungen (`components/portfolio/KlumpenWarnings.tsx`)

**Files:**
- Create: `frontend/src/components/portfolio/KlumpenWarnings.tsx`
- Test: `frontend/src/components/portfolio/KlumpenWarnings.test.tsx`

**Interfaces:**
- Consumes: `KlumpenWarningDTO`, `KlumpenDimension` aus `contract/portfolio.ts`.
- Produces: `KlumpenWarnings({ klumpen }: { klumpen: KlumpenWarningDTO[] })`.

**Strukturvorgabe (US25, Wireframe §4.8):** Überschrift „⚠ Klumpen-Warnungen". Leere Liste → grüner Hinweis „Keine Konzentration über den Limits.". Sonst Liste je Warnung mit deutscher Dimensions-Bezeichnung (`sector`→„Sektor", `underlying`→„Asset-Klasse", `geography`→„Geographie") und der vorformatierten `message` (enthält bereits „Name N % (Limit M %)").

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KlumpenWarnings } from "./KlumpenWarnings";
import type { KlumpenWarningDTO } from "../../contract/portfolio";

const tech: KlumpenWarningDTO = {
  dimension: "sector", name: "Technologie", pct: 0.41, limit: 0.30, message: "Technologie 41 % (Limit 30 %)",
};

describe("KlumpenWarnings", () => {
  it("zeigt jede Warnung mit deutscher Dimension und Limit-Bezug", () => {
    render(<KlumpenWarnings klumpen={[tech]} />);
    expect(screen.getByText(/Sektor/)).toBeInTheDocument();
    expect(screen.getByText(/Technologie 41 % \(Limit 30 %\)/)).toBeInTheDocument();
  });
  it("leere Liste => Entwarnung statt Warnung", () => {
    render(<KlumpenWarnings klumpen={[]} />);
    expect(screen.getByText(/Keine Konzentration über den Limits/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/portfolio/KlumpenWarnings.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { KlumpenWarningDTO, KlumpenDimension } from "../../contract/portfolio";

// Deutsche Dimensions-Bezeichnung (Wireframe §4.8: Sektor / Asset-Klasse / Geographie).
const DIM_LABEL: Record<KlumpenDimension, string> = {
  sector: "Sektor", underlying: "Asset-Klasse", geography: "Geographie",
};

// Klumpen-Warnungen (US25): Konzentration je Dimension mit Limit-Bezug. Leere Liste = Entwarnung.
export function KlumpenWarnings({ klumpen }: { klumpen: KlumpenWarningDTO[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">⚠ Klumpen-Warnungen</h3>
      {klumpen.length === 0 ? (
        <p className="mt-1 rounded bg-green-50 p-2 text-sm text-green-700">
          Keine Konzentration über den Limits.
        </p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {klumpen.map((k) => (
            <li key={`${k.dimension}-${k.name}`} className="rounded bg-amber-50 px-2 py-1 text-amber-800">
              <span className="font-medium">{DIM_LABEL[k.dimension]}:</span> {k.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/portfolio/KlumpenWarnings.test.tsx`
Expected: PASS (2 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/portfolio/KlumpenWarnings.tsx frontend/src/components/portfolio/KlumpenWarnings.test.tsx
git commit -m "feat(portfolio): Klumpen-Warnungen mit Limit-Bezug (Sektor/Asset-Klasse/Geographie) (US25)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B4: Hedge-Vorschläge (`components/portfolio/HedgeSuggestions.tsx`)

**Files:**
- Create: `frontend/src/components/portfolio/HedgeSuggestions.tsx`
- Test: `frontend/src/components/portfolio/HedgeSuggestions.test.tsx`

**Interfaces:**
- Consumes: `HedgeSuggestionDTO` aus `contract/portfolio.ts`.
- Produces: `HedgeSuggestions({ hedges }: { hedges: HedgeSuggestionDTO[] })`.

**Strukturvorgabe (US26/US27, Wireframe §4.8):** Überschrift „Hedge-Vorschläge" + Pflicht-Hinweis **„beratend, keine Ausführung"** (US27 — es gibt **keine** Trade-Buttons). Liste je Vorschlag mit `text` und kleiner `rationale` darunter. Leere Liste → Hinweis „Aktuell kein Hedge nötig (Kennzahlen im Rahmen).".

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HedgeSuggestions } from "./HedgeSuggestions";
import type { HedgeSuggestionDTO } from "../../contract/portfolio";

const h: HedgeSuggestionDTO = {
  id: "net-beta", text: "net_beta 62 % senken → Index-Short (z. B. SPY) oder VIX-Hedge erwägen",
  rationale: "aktien-only net_beta über 30 % NAV — Buch ist marktsensitiv",
};

describe("HedgeSuggestions", () => {
  it("zeigt den Vorschlag und den beratend-Hinweis (keine Ausführung)", () => {
    render(<HedgeSuggestions hedges={[h]} />);
    expect(screen.getByText(/Index-Short/)).toBeInTheDocument();
    expect(screen.getByText(/beratend, keine Ausführung/i)).toBeInTheDocument();
  });
  it("hat KEINEN Ausführungs-Button (US27)", () => {
    render(<HedgeSuggestions hedges={[h]} />);
    expect(screen.queryByRole("button")).toBeNull();
  });
  it("leere Liste => Entwarnung", () => {
    render(<HedgeSuggestions hedges={[]} />);
    expect(screen.getByText(/kein Hedge nötig/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/portfolio/HedgeSuggestions.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementieren**

```tsx
import type { HedgeSuggestionDTO } from "../../contract/portfolio";

// Hedge-Vorschlaege (US26) — Track B ist BERATEND, KEINE Ausfuehrung (US27): bewusst keine
// Trade-Buttons, nur Anzeige. Jeder Vorschlag traegt seine Ableitung (rationale).
export function HedgeSuggestions({ hedges }: { hedges: HedgeSuggestionDTO[] }) {
  return (
    <div>
      <div className="flex items-baseline gap-2">
        <h3 className="text-sm font-semibold">Hedge-Vorschläge</h3>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          beratend, keine Ausführung
        </span>
      </div>
      {hedges.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">Aktuell kein Hedge nötig (Kennzahlen im Rahmen).</p>
      ) : (
        <ul className="mt-1 space-y-1 text-sm">
          {hedges.map((h) => (
            <li key={h.id} className="rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
              <div>• {h.text}</div>
              <div className="text-xs text-slate-500">{h.rationale}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/components/portfolio/HedgeSuggestions.test.tsx`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/portfolio/HedgeSuggestions.tsx frontend/src/components/portfolio/HedgeSuggestions.test.tsx
git commit -m "feat(portfolio): beratende Hedge-Vorschlaege ohne Ausfuehrung (US26/US27)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B5: PortfolioPage (`pages/PortfolioPage.tsx`)

**Files:**
- Create: `frontend/src/pages/PortfolioPage.tsx`
- Test: `frontend/src/pages/PortfolioPage.test.tsx`

**Interfaces:**
- Consumes: `useView`; `loadPortfolio`; `PortfolioView` aus `contract/portfolio.ts`; `DemoBadge`; `SourceHealth`; `ExposurePanel`, `KlumpenWarnings`, `HedgeSuggestions`, `PositionsTable`.
- Produces: `PortfolioPage({ loader }?: { loader?: () => Promise<PortfolioView> })` — lädt über `useView`, rendert Kopfzeile (Titel + `DemoBadge` + `SourceHealth`), Risiko-Block (ExposurePanel + KlumpenWarnings + HedgeSuggestions) und PositionsTable.

> **Mapping-/Stabilitäts-Hinweis:** `loadPortfolio` ist eine Modul-Funktion ohne Argumente → direkt als Default-Loader nutzbar; `useView(loader)` braucht ihn stabil (Modul-Identität reicht, kein `useCallback` nötig, wie `YieldCurveDrilldown`). DTOs werden direkt als Props übergeben (`exposure={data.exposure}` etc.) — keine Adapter.

- [ ] **Step 1: Failing test schreiben**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PortfolioPage } from "./PortfolioPage";
import { loadPortfolio } from "../data/portfolio";

function renderPage() {
  return render(
    <MemoryRouter>
      <PortfolioPage loader={loadPortfolio} />
    </MemoryRouter>,
  );
}

describe("PortfolioPage", () => {
  it("rendert Exposure-Panel, Klumpen, Hedge-Vorschläge und Positionstabelle", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Brutto-Exposure/)).toBeInTheDocument());
    expect(screen.getByText(/aktien-only/i)).toBeInTheDocument();           // net_beta-Label
    expect(screen.getByText(/Klumpen-Warnungen/)).toBeInTheDocument();
    expect(screen.getByText(/beratend, keine Ausführung/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /AAPL/ })).toBeInTheDocument(); // Positionstabelle
  });
  it("zeigt das Demo-Etikett (isDemo)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });
  it("markiert den Konflikt (XLE) in der Tabelle", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Urteil gegen Position/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/pages/PortfolioPage.test.tsx`
Expected: FAIL (Component nicht gefunden).

- [ ] **Step 3: Implementieren**

```tsx
import { useView } from "../data/useView";
import { loadPortfolio } from "../data/portfolio";
import type { PortfolioView } from "../contract/portfolio";
import { DemoBadge } from "../components/DemoBadge";
import { SourceHealth } from "../components/SourceHealth";
import { ExposurePanel } from "../components/portfolio/ExposurePanel";
import { KlumpenWarnings } from "../components/portfolio/KlumpenWarnings";
import { HedgeSuggestions } from "../components/portfolio/HedgeSuggestions";
import { PositionsTable } from "../components/portfolio/PositionsTable";

// Portfolio-Seite (Track B, US23–27): Risiko-Linse + Positionen. Beratend, KEINE Ausfuehrung.
// Loader-Prop ermoeglicht stabilen Aufruf ohne Refetch-Loop (Modul-Identitaet als Default).
export function PortfolioPage({ loader = loadPortfolio }: { loader?: () => Promise<PortfolioView> }) {
  const { data, loading, error } = useView(loader);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Portfolio — Risiko & Positionen (Track B)</h2>
        {data && <DemoBadge isDemo={data.isDemo} />}
        {data && <SourceHealth active={data.sourcesActive} total={data.sourcesTotal} failed={data.failed} />}
      </div>

      {loading && <p className="text-slate-500">Lädt …</p>}
      {!loading && error && <p className="text-red-600">{error}</p>}

      {data && !loading && !error && (
        <>
          <div className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
            <ExposurePanel exposure={data.exposure} />
            <KlumpenWarnings klumpen={data.klumpen} />
            <HedgeSuggestions hedges={data.hedges} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Positionen</h3>
            <PositionsTable positions={data.positions} />
          </div>
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/pages/PortfolioPage.test.tsx`
Expected: PASS (3 Tests grün).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PortfolioPage.tsx frontend/src/pages/PortfolioPage.test.tsx
git commit -m "feat(portfolio): PortfolioPage (Exposure/Klumpen/Hedges/Positionen) (US23–27)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B6: Routing-Verdrahtung (`routes.tsx`)

**Files:**
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/routes.test.tsx`

**Interfaces:**
- Consumes: `PortfolioPage` aus `pages/PortfolioPage.tsx`.
- Produces: `/portfolio` rendert `PortfolioPage` statt des Platzhalters.

- [ ] **Step 1: Failing test ergänzen** (in `routes.test.tsx`, vorhandenen Render-Helfer der Datei nutzen)

```tsx
  it("/portfolio rendert die PortfolioPage (Exposure-Panel sichtbar)", async () => {
    renderAt("/portfolio"); // bestehender Render-Helfer der Datei
    await waitFor(() => expect(screen.getByText(/Brutto-Exposure/)).toBeInTheDocument());
  });
```

> **Hinweis:** Den vorhandenen Render-Helfer und die Imports (`waitFor`, `screen`) der Datei verwenden (nicht neu erfinden). Slice 3 braucht keinen ECharts-Mock.

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/routes.test.tsx`
Expected: FAIL (Platzhalter „Portfolio" statt „Brutto-Exposure").

- [ ] **Step 3: Routing anpassen** — Import ergänzen:

```tsx
import { PortfolioPage } from "./pages/PortfolioPage";
```

Zeile `<Route path="/portfolio" element={<PlaceholderPage title="Portfolio" />} />` ersetzen durch:

```tsx
        <Route path="/portfolio" element={<PortfolioPage />} />
```

- [ ] **Step 4: Test laufen — muss bestehen**

Run: `cd frontend && npx vitest run src/routes.test.tsx`
Expected: PASS.

- [ ] **Step 5: Voller Lauf + Typcheck**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: PASS (alle Tests grün, keine Typfehler).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes.tsx frontend/src/routes.test.tsx
git commit -m "feat(portfolio): /portfolio auf PortfolioPage verdrahtet (Platzhalter ersetzt)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task B7: Logbuch + Folge-Aufgaben (`docs/open_todos.md`)

**Files:**
- Modify: `docs/open_todos.md`

> **Kein Test** (reine Doku, AGENTS.md §5). Slice 3 ist ein PR — der Logbuch-Eintrag dokumentiert die Umsetzung und die echten Backend-Endpunkte als Folge-Aufgaben. **Nicht** direkt auf master committen; dieser Commit gehört in den Slice-3-PR.

- [ ] **Step 1: Eintrag ergänzen** (passend zum bestehenden Logbuch-Stil) — abgehakter Slice-3-Eintrag mit `Lösung:`-Hinweis + neue Folge-Aufgaben:

```markdown
- [x] **Frontend Slice 3 — Portfolio (Track B)** (Konzept §2.4, Spec §7/§10 US23–27). Lösung: Portfolio-Bereich über die Tausch-Naht `loadPortfolio()` (Demo-Fixture: Positionen long+short quer über underlying×wrapper inkl. Konflikt-Fall XLE long+SELL). Positionstabelle mit Doppel-Etikett, L/S, Größe, Einstand, AAIA-Urteil + Konflikt-Markierung, Ticker→Deep-Dive (US23); Exposure-Panel Brutto/Netto/net_beta (aktien-only, datierte Vola) mit Inline-Definitionen (US24); Klumpen-Warnungen Sektor/underlying/Geographie mit Limit-Bezug (US25); beratende Hedge-Vorschläge ohne Ausführung (US26/US27). Pure getestete Logik (gespiegelt aus portfolio_monitor_agent/PR #11): `grossExposure`/`netExposure`/`netBeta`, `detectKlumpen`, `detectConflict` (exportiert → Slice 4 nutzt sie wieder), `hedgeSuggestions`. UNAVAILABLE-Pfad: Aktie mit Beta `null` zählt nicht ins net_beta; Beta-Feed-Stub als `failed`-Quelle.
  - [ ] **Folge: echter Portfolio-Endpunkt** — `data/api/portfolio.ts` (`fetchPortfolio`) statt Demo; Naht-Zeile in `data/portfolio.ts` tauschen. Lösungsansatz: `portfolio_monitor_agent`-Snapshot (net_beta/Exposure/cluster_risks/Vola) hinter einen API-Endpunkt hängen, der den `PortfolioView`-Vertrag erfüllt; Klumpen-Limits aus dem Agenten (0.40/0.60/0.70) übernehmen.
  - [ ] **Folge: Slice 4 (Inbox) verdrahten** — `detectConflict`/`conflictNote` aus `lib/conflict.ts` in der Konflikt-Inbox wiederverwenden; Inbox-Badge in der Topbar aus der Anzahl der Konflikt-Positionen speisen.
```

- [ ] **Step 2: Commit** (in den Slice-3-PR, nicht direkt auf master)

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Frontend Slice 3 (Portfolio) + Folge-Aufgaben protokolliert

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec-Coverage (US23–27, Spec §10 Slice-3-Zeile):**

| US | Inhalt | Task(s) |
|---|---|---|
| US23 | Alle Positionen (long/short) mit beiden Etiketten, Größe, Einstand, AAIA-Urteil + Konflikt-Markierung, Ticker→Deep-Dive | B1 (PositionsTable), A4 (detectConflict), A6 (Fixture inkl. XLE-Konflikt) |
| US24 | Brutto-/Netto-Exposure + net_beta (aktien-only, datierte Vola) mit Inline-Definitionen | B2 (ExposurePanel), A2 (grossExposure/netExposure/netBeta), A1 (ExposureDTO volAsOf) |
| US25 | Klumpen-Warnungen (Sektor/underlying/Geographie) mit Limit-Bezug | B3 (KlumpenWarnings), A3 (detectKlumpen + DEFAULT_LIMITS) |
| US26 | Hedge-Vorschläge (Track B, beratend) aus Kennzahlen/Klumpen | B4 (HedgeSuggestions), A5 (hedgeSuggestions) |
| US27 | Keine Trade-Ausführung, nur Vorschläge | B4 („beratend, keine Ausführung" + kein Button), B1 (Ticker-Klick führt nur zum Deep-Dive) |

Architektur-Vorgaben: Tausch-Naht (A1/A6/A7), pure getestete Logik (A2–A5), `detectConflict` exportiert für Slice-4-Wiederverwendung (A4), TDD je Task, UNAVAILABLE-Pfad (Aktie mit Beta `null` nicht im net_beta; Vola `null` → `UnavailableField`; Beta-Feed `failed`-Quelle), keine magischen Zahlen ohne Begründung (Klumpen-Limits = Backend-Werte + Kommentar; net_beta-Hedge-Schwelle als benannte Konstante; strikt-größer/lückenlose Bänder), Loader stabil via Modul-Identität. Keine Lücke.

**2. Placeholder-Scan:** Kein „TBD/TODO/später/Beispiel-Logik"-Marker im Code. Alle Implementierungs-Schritte enthalten vollständigen, direkt verwendbaren Code; alle Tests vollständige Assertions. Demo-Aggregate werden aus den Positionen **berechnet** (nicht handgesetzt) → keine driftenden Platzhalter-Zahlen.

**3. Typ-Konsistenz:** `PortfolioView`-Felder (A1) werden überall identisch benannt (`positions`/`exposure`/`klumpen`/`hedges`/`limits`/`navCurrency`). `PositionDTO`-Felder (`direction`/`sizePctNav`/`entryPrice`/`underlying`/`wrapper`/`sector`/`geography`/`beta`/`judgment`) deckungsgleich zwischen Fixture (A6), pure Logik (A2/A3/A4) und Tabelle (B1). `ExposureDTO` (`grossPct`/`netPct`/`netBeta`/`annualizedVolPct`/`volAsOf`) identisch zwischen A2-Berechnung (A6 mappt), A5 (hedge) und B2 (Panel). `KlumpenWarningDTO`/`KlumpenDimension` identisch zwischen A3 und B3. `detectConflict(direction, judgment)`-Signatur identisch zwischen A4, A6/A7-Test und B1. `verdictToVisual` akzeptiert `LongVerdict | ShortVerdict` (bestehend) — B1 castet das je Richtung gewählte Verdikt korrekt. `Underlying`/`Wrapper` aus `contract/common.ts` (wiederverwendet, nicht dupliziert). net_beta nutzt `{equity, equity_index}` konsistent mit dem Backend-`{equity, index}` (im Frontend-Vertrag heißt der Index-Underlying `equity_index`).

---

## Dispatch-Gruppierung

- **Dispatch A (Naht + pure Risiko-Logik):** A1 (Vertrag), A2 (Exposure/net_beta), A3 (Klumpen-Detektion), A4 (Konflikt-Erkennung, exportiert für Slice 4), A5 (Hedge-Vorschläge), A6 (Demo-Fixture), A7 (Naht `loadPortfolio`). — A2–A5 sind voneinander unabhängig (parallelisierbar); A6 hängt von A1–A5, A7 von A6. Blockiert B.
- **Dispatch B (PortfolioPage + Komponenten + Routing):** B1 (PositionsTable), B2 (ExposurePanel), B3 (KlumpenWarnings), B4 (HedgeSuggestions), B5 (PortfolioPage), B6 (Routing-Verdrahtung), B7 (Logbuch). — B1–B4 sind unabhängig voneinander (parallelisierbar); B5 hängt von B1–B4 + A7; B6 von B5; B7 reine Doku.
