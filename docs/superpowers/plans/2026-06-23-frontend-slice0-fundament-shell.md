# Frontend Slice 0 — Fundament + Shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Das Frontend-Fundament bauen — Router + App-Shell (Sidebar/Topbar), die austauschbare Daten-Naht (`contract/` + `data/` + `DemoBadge`), die gemeinsame Komponenten-Bibliothek (Doppel-Etikett, Long/Short-Panel, XAI, Schwellen-Badges, Anomalie-Report, Quellen-Health) und ein ECharts-Wrapper-Referenzmuster — so dass die Cockpit-Übersicht in der Shell läuft und alle weiteren Slices darauf aufsetzen.

**Architecture:** Erweiterung des bestehenden `frontend/`-Pakets (React 19 + TS + Vite + Tailwind v3 + Vitest). Reine Anzeige-Logik als pure, zuerst getestete Funktionen in `src/lib/`. Daten je Bereich über genau eine `load*()`-Naht (`src/data/`), die heute Demo-Fixtures (`src/data/demo/`) liefert und deren echte Variante (`src/data/api/`) als vorbereitete Zeile daneben steht; jeder Vertrag (`src/contract/`) trägt `isDemo`. Routing via `react-router-dom`; die Shell umschließt alle Bereiche hinter dem bestehenden `LoginGate`.

**Tech Stack:** React 19, TypeScript, Vite 8, Tailwind CSS v3, Vitest 4 + React Testing Library (jsdom), react-router-dom v7, echarts + echarts-for-react.

## Global Constraints

- **Sprache:** UI-Texte und Code-Kommentare auf **Deutsch**; Commit-Präfixe `feat(...)`, `test(...)`, `chore(...)`, `docs(...)`.
- **TDD verpflichtend (AGENTS.md §4):** erst der fehlschlagende Test, dann minimaler Code bis grün. Pure Anzeige-Logik wird **zuerst** getestet; Grenzfälle explizit (genau auf Schwelle, knapp darüber/darunter, `null`, negativ).
- **Monorepo:** gesamter Frontend-Code unter `frontend/`. Python-Backend unberührt.
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL** (Konzept §5.4): ausgefallene Quelle → eigener Zustand, nie grün/neutral.
- **Demo ≠ UNAVAILABLE** (Spec §1): Demo = ganze Ansicht aus Beispielwerten (sichtbares `DemoBadge`, `isDemo:true`); UNAVAILABLE = einzelne Quelle innerhalb eines Ergebnisses ausgefallen.
- **Tausch-Naht (Spec §2):** genau eine `load*()`-Funktion pro Bereich; Demo- und Echt-Implementierung liefern denselben Vertrag; Umstieg = eine Zeile / `VITE_DATA_MODE`-Schalter; `isDemo` steuert das `DemoBadge` automatisch.
- **Fachliche Korrektheit (AGENTS.md §3):** Vorzeichen/Richtung benannt (Contango → Roll-Yield negativ; Spread `10J−2J`); keine magischen Zahlen ohne Begründung im Kommentar.
- **Bestehendes wiederverwenden:** `SignalBadge`, `ConfidenceBar`, `UnavailableField`, `formatConfidence`, `signalToVisual`, `isUnavailable`, `sourcesLabel`, `useAuth`, `LoginGate`, `useCockpit` bleiben erhalten und werden nicht dupliziert.
- Test gezielt: `cd frontend && npx vitest run <pfad>`; gesamt: `cd frontend && npm test`; Build: `cd frontend && npm run build`.

---

## File Structure

| Datei | Verantwortung |
|---|---|
| `frontend/src/lib/assets.ts` (+ `.test.ts`) | pure: `underlyingToVisual`, `wrapperToVisual` |
| `frontend/src/lib/judgment.ts` (+ `.test.ts`) | pure: `confidenceFlags`, `consistencyHint`, `verdictToVisual` |
| `frontend/src/lib/futures.ts` (+ `.test.ts`) | pure: `rollYieldVisual`, `leverageFactor` |
| `frontend/src/lib/curve.ts` (+ `.test.ts`) | pure: `yieldSpreadStatus` |
| `frontend/src/lib/anomaly.ts` (+ `.test.ts`) | pure: `zScoreFlag`, `anomalySeverityToVisual` |
| `frontend/src/contract/common.ts` | Basis-Vertragstypen + `DemoMeta` (`isDemo`), Enums `Underlying`/`Wrapper`/`LongVerdict`/`ShortVerdict`/`AnomalySeverity` |
| `frontend/src/data/dataMode.ts` (+ `.test.ts`) | pure: `resolveDataMode(env)` (`demo`/`real`/`auto`) |
| `frontend/src/data/apiDeps.ts` | `interface ApiDeps { base?: string; fetchFn?: typeof fetch; token?: string \| null }` |
| `frontend/src/components/DemoBadge.tsx` (+ `.test.tsx`) | „Demo-Daten"-Etikett, gesteuert über `isDemo` |
| `frontend/src/components/UnderlyingWrapperBadge.tsx` (+ `.test.tsx`) | Doppel-Etikett |
| `frontend/src/components/ThresholdBadges.tsx` (+ `.test.tsx`) | `AutoHoldBadge`, `CashBiasBadge` (aus `confidenceFlags`) |
| `frontend/src/components/XaiPanel.tsx` (+ `.test.tsx`) | aufklappbares XAI-Panel |
| `frontend/src/components/LongShortPanel.tsx` (+ `.test.tsx`) | zwei gleichwertige Urteils-Spalten |
| `frontend/src/components/AnomalyReport.tsx` (+ `.test.tsx`) | Anomalie-Anzeige |
| `frontend/src/components/SourceHealth.tsx` (+ `.test.tsx`) | „x/y Quellen aktiv" + Liste ausgefallener Quellen |
| `frontend/src/components/charts/ChartContainer.tsx` | gemeinsamer Lazy-/Theme-Rahmen für ECharts |
| `frontend/src/components/charts/LineCurve.tsx` (+ `.test.tsx`) | Referenz-Chart-Wrapper (Linie) |
| `frontend/src/shell/Sidebar.tsx` (+ `.test.tsx`) | linke Navigation |
| `frontend/src/shell/Topbar.tsx` (+ `.test.tsx`) | Suche/Inbox-Badge/Health/Theme/Logout |
| `frontend/src/shell/AppShell.tsx` (+ `.test.tsx`) | Layout-Rahmen, rendert `<Outlet/>` |
| `frontend/src/shell/useTheme.ts` (+ `.test.tsx`) | hell/dunkel, persistiert |
| `frontend/src/routes.tsx` | Router-Definition (Bereiche als Platzhalter-Seiten) |
| `frontend/src/pages/PlaceholderPage.tsx` | generische „in Arbeit"-Seite für noch leere Bereiche |
| `frontend/src/App.tsx` (modify) | LoginGate + RouterProvider |
| `frontend/package.json` (modify) | Abhängigkeiten react-router-dom, echarts, echarts-for-react |
| `frontend/tailwind.config.js` (modify) | `darkMode: "class"` |
| `frontend/.env.example` (modify) | `VITE_DATA_MODE` dokumentiert |

---

## Task 1: Abhängigkeiten + Tailwind-Dark-Mode

**Files:**
- Modify: `frontend/package.json`, `frontend/tailwind.config.js`, `frontend/.env.example`

**Interfaces:**
- Produces: installierte Pakete `react-router-dom@^7`, `echarts@^5`, `echarts-for-react@^3`; Tailwind `darkMode: "class"`.

- [ ] **Step 1: Pakete installieren**

Aus dem Worktree-Wurzelverzeichnis:
```bash
cd frontend
npm install react-router-dom echarts echarts-for-react
```

- [ ] **Step 2: Tailwind Dark-Mode aktivieren**

`frontend/tailwind.config.js` — `darkMode: "class"` ergänzen:
```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

- [ ] **Step 3: `.env.example` ergänzen**

An `frontend/.env.example` anhängen:
```
# Datenquelle der noch nicht angebundenen Bereiche: demo | real | auto (Default: auto).
# auto => jede Naht entscheidet selbst (heute Demo). Cockpit-Uebersicht ist immer echt.
VITE_DATA_MODE=auto
```

- [ ] **Step 4: Build prüfen + Commit**

Run: `cd frontend && npm run build`
Expected: Build erfolgreich.
```bash
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.js frontend/.env.example
git commit -m "chore(frontend): react-router-dom + echarts Abhaengigkeiten, Tailwind Dark-Mode, VITE_DATA_MODE"
```

---

## Task 2: Vertrag-Basistypen + Daten-Modus + ApiDeps

**Files:**
- Create: `frontend/src/contract/common.ts`, `frontend/src/data/apiDeps.ts`, `frontend/src/data/dataMode.ts`
- Test: `frontend/src/data/dataMode.test.ts`

**Interfaces:**
- Produces (`common.ts`): `interface DemoMeta { isDemo: boolean }`; `type Underlying = "equity" | "equity_index" | "bond" | "commodity" | "precious_metal"`; `type Wrapper = "single" | "fund" | "future" | "physical_etc"`; `type LongVerdict = "BUY" | "SELL" | "HOLD" | "NONE"`; `type ShortVerdict = "SHORT" | "COVER" | "HOLD" | "NONE"`; `type AnomalySeverity = "none" | "low" | "medium" | "high"`.
- Produces (`apiDeps.ts`): `interface ApiDeps { base?: string; fetchFn?: typeof fetch; token?: string | null }`.
- Produces (`dataMode.ts`): `type DataMode = "demo" | "real" | "auto"`; `resolveDataMode(env: string | undefined): DataMode` (unbekannt/leer → `"auto"`).

- [ ] **Step 1: Typen schreiben (keine Tests — reine Typen)**

`frontend/src/contract/common.ts`:
```ts
// Basis-Vertragstypen, die Demo- und Echt-Quellen gemeinsam erfuellen (Spec §2).
// isDemo steuert das DemoBadge automatisch (true=Beispielwerte, false=echt).
export interface DemoMeta {
  isDemo: boolean;
}

export type Underlying = "equity" | "equity_index" | "bond" | "commodity" | "precious_metal";
export type Wrapper = "single" | "fund" | "future" | "physical_etc";

// Long- und Short-Linse sind gleichwertig (Konzept §2.3).
export type LongVerdict = "BUY" | "SELL" | "HOLD" | "NONE";
export type ShortVerdict = "SHORT" | "COVER" | "HOLD" | "NONE";

export type AnomalySeverity = "none" | "low" | "medium" | "high";
```

`frontend/src/data/apiDeps.ts`:
```ts
// Gemeinsame Abhaengigkeiten jeder Daten-Naht (injizierbar -> testbar gegen Fakes).
export interface ApiDeps {
  base?: string;
  fetchFn?: typeof fetch;
  token?: string | null;
}
```

- [ ] **Step 2: Failing-Test für `resolveDataMode`**

`frontend/src/data/dataMode.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { resolveDataMode } from "./dataMode";

describe("resolveDataMode", () => {
  it("erkennt explizite Modi", () => {
    expect(resolveDataMode("demo")).toBe("demo");
    expect(resolveDataMode("real")).toBe("real");
    expect(resolveDataMode("auto")).toBe("auto");
  });
  it("faellt bei leer/unbekannt auf auto zurueck", () => {
    expect(resolveDataMode(undefined)).toBe("auto");
    expect(resolveDataMode("")).toBe("auto");
    expect(resolveDataMode("quatsch")).toBe("auto");
  });
});
```

- [ ] **Step 3: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/data/dataMode.test.ts`
Expected: FAIL (`Failed to resolve import "./dataMode"`).

- [ ] **Step 4: Implementieren**

`frontend/src/data/dataMode.ts`:
```ts
export type DataMode = "demo" | "real" | "auto";

// Liest den globalen Daten-Modus aus VITE_DATA_MODE; Default/Unbekannt => "auto".
export function resolveDataMode(env: string | undefined): DataMode {
  if (env === "demo" || env === "real" || env === "auto") return env;
  return "auto";
}
```

- [ ] **Step 5: Test grün + Commit**

Run: `cd frontend && npx vitest run src/data/dataMode.test.ts` → PASS.
```bash
git add frontend/src/contract/common.ts frontend/src/data/apiDeps.ts frontend/src/data/dataMode.ts frontend/src/data/dataMode.test.ts
git commit -m "feat(frontend): Vertrag-Basistypen + ApiDeps + resolveDataMode (Tausch-Naht-Fundament)"
```

---

## Task 3: Pure Anzeige-Logik — Assets (underlying/wrapper)

**Files:**
- Create: `frontend/src/lib/assets.ts`
- Test: `frontend/src/lib/assets.test.ts`

**Interfaces:**
- Consumes: `Underlying`, `Wrapper` (Task 2).
- Produces: `interface BadgeVisual { label: string; icon: string; colorClass: string }`; `underlyingToVisual(u: Underlying): BadgeVisual`; `wrapperToVisual(w: Wrapper): BadgeVisual`.

- [ ] **Step 1: Failing-Test**

`frontend/src/lib/assets.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { underlyingToVisual, wrapperToVisual } from "./assets";

describe("underlyingToVisual", () => {
  it("liefert Label + Icon je Basiswert", () => {
    expect(underlyingToVisual("precious_metal")).toMatchObject({ label: "Edelmetall", icon: "🥇" });
    expect(underlyingToVisual("equity")).toMatchObject({ label: "Aktie", icon: "🏢" });
    expect(underlyingToVisual("equity_index")).toMatchObject({ label: "Index", icon: "📈" });
    expect(underlyingToVisual("bond")).toMatchObject({ label: "Anleihe", icon: "🏛" });
    expect(underlyingToVisual("commodity")).toMatchObject({ label: "Rohstoff", icon: "🛢" });
  });
});

describe("wrapperToVisual", () => {
  it("liefert Label + Icon je Huelle", () => {
    expect(wrapperToVisual("future")).toMatchObject({ label: "Future", icon: "⏳" });
    expect(wrapperToVisual("single")).toMatchObject({ label: "Einzeltitel" });
    expect(wrapperToVisual("fund")).toMatchObject({ label: "Fonds" });
    expect(wrapperToVisual("physical_etc")).toMatchObject({ label: "Physisch (ETC)" });
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/assets.test.ts` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/lib/assets.ts`:
```ts
import type { Underlying, Wrapper } from "../contract/common";

export interface BadgeVisual {
  label: string;
  icon: string;
  colorClass: string;
}

// Basiswert (underlying) -> Anzeige. Material-/Form-Icon je Anlageklasse (Konzept §5.2).
export function underlyingToVisual(u: Underlying): BadgeVisual {
  switch (u) {
    case "equity":         return { label: "Aktie",     icon: "🏢", colorClass: "bg-sky-100 text-sky-800" };
    case "equity_index":   return { label: "Index",     icon: "📈", colorClass: "bg-indigo-100 text-indigo-800" };
    case "bond":           return { label: "Anleihe",   icon: "🏛", colorClass: "bg-emerald-100 text-emerald-800" };
    case "commodity":      return { label: "Rohstoff",  icon: "🛢", colorClass: "bg-amber-100 text-amber-800" };
    case "precious_metal": return { label: "Edelmetall", icon: "🥇", colorClass: "bg-yellow-100 text-yellow-800" };
  }
}

// Huelle (wrapper) -> Anzeige.
export function wrapperToVisual(w: Wrapper): BadgeVisual {
  switch (w) {
    case "single":       return { label: "Einzeltitel",   icon: "•",  colorClass: "bg-slate-100 text-slate-700" };
    case "fund":         return { label: "Fonds",         icon: "▣",  colorClass: "bg-slate-100 text-slate-700" };
    case "future":       return { label: "Future",        icon: "⏳", colorClass: "bg-orange-100 text-orange-800" };
    case "physical_etc": return { label: "Physisch (ETC)", icon: "⛃", colorClass: "bg-slate-100 text-slate-700" };
  }
}
```

- [ ] **Step 4: Test grün + Commit**

Run: `cd frontend && npx vitest run src/lib/assets.test.ts` → PASS.
```bash
git add frontend/src/lib/assets.ts frontend/src/lib/assets.test.ts
git commit -m "feat(frontend): pure underlyingToVisual/wrapperToVisual (Doppel-Etikett-Logik)"
```

---

## Task 4: Pure Anzeige-Logik — Judgment (Konfidenz-Flags, Konsistenz, Verdikt)

**Files:**
- Create: `frontend/src/lib/judgment.ts`
- Test: `frontend/src/lib/judgment.test.ts`

**Interfaces:**
- Consumes: `LongVerdict`, `ShortVerdict` (Task 2).
- Produces: `interface ConfidenceFlags { autoHold: boolean; cashBias: boolean }`; `confidenceFlags(value: number): ConfidenceFlags` (autoHold wenn <0.50, cashBias wenn <0.35); `consistencyHint(long: LongVerdict, short: ShortVerdict): string | null`; `verdictToVisual(v: LongVerdict | ShortVerdict): { label: string; colorClass: string }`.

- [ ] **Step 1: Failing-Test**

`frontend/src/lib/judgment.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { confidenceFlags, consistencyHint, verdictToVisual } from "./judgment";

describe("confidenceFlags", () => {
  it("auto-HOLD ab unter 0.50, Cash-Bias ab unter 0.35 (Konzept/frontend_notes)", () => {
    expect(confidenceFlags(0.60)).toEqual({ autoHold: false, cashBias: false });
    expect(confidenceFlags(0.50)).toEqual({ autoHold: false, cashBias: false }); // genau auf Schwelle: nicht ausgeloest
    expect(confidenceFlags(0.49)).toEqual({ autoHold: true, cashBias: false });
    expect(confidenceFlags(0.35)).toEqual({ autoHold: true, cashBias: false }); // genau auf Schwelle
    expect(confidenceFlags(0.34)).toEqual({ autoHold: true, cashBias: true });
  });
});

describe("consistencyHint", () => {
  it("beide bearish -> starkes bearishes Gesamtbild", () => {
    expect(consistencyHint("SELL", "SHORT")).toMatch(/bearish/i);
  });
  it("beide schwach/NONE -> kein Edge", () => {
    expect(consistencyHint("NONE", "NONE")).toMatch(/kein Edge/i);
  });
  it("gemischt -> kein Hinweis", () => {
    expect(consistencyHint("BUY", "NONE")).toBeNull();
  });
});

describe("verdictToVisual", () => {
  it("BUY/COVER gruen, SELL/SHORT rot, HOLD grau-blau, NONE grau", () => {
    expect(verdictToVisual("BUY").colorClass).toContain("green");
    expect(verdictToVisual("COVER").colorClass).toContain("green");
    expect(verdictToVisual("SELL").colorClass).toContain("red");
    expect(verdictToVisual("SHORT").colorClass).toContain("red");
    expect(verdictToVisual("HOLD").colorClass).toContain("slate");
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/judgment.test.ts` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/lib/judgment.ts`:
```ts
import type { LongVerdict, ShortVerdict } from "../contract/common";

export interface ConfidenceFlags {
  autoHold: boolean;  // Konfidenz < 0.50 -> automatisch HOLD (zu unsicher)
  cashBias: boolean;  // Konfidenz < 0.35 -> zusaetzlich Cash-Bias
}

// Schwellen aus frontend_notes.md / Konzept §2.3. STRIKT kleiner: genau auf der
// Schwelle wird NICHT ausgeloest (lueckenlose Baender, AGENTS.md §2).
export function confidenceFlags(value: number): ConfidenceFlags {
  return { autoHold: value < 0.5, cashBias: value < 0.35 };
}

const BEARISH = new Set<string>(["SELL", "SHORT"]);
const WEAK = new Set<string>(["NONE", "HOLD"]);

// Konsistenz-Hinweis ueber beide Linsen (Konzept §5.3).
export function consistencyHint(long: LongVerdict, short: ShortVerdict): string | null {
  if (BEARISH.has(long) && BEARISH.has(short)) return "Beide Linsen bearish — starkes bearishes Gesamtbild.";
  if (WEAK.has(long) && WEAK.has(short)) return "Beide Linsen schwach — kein Edge.";
  return null;
}

// Urteil-Wort -> Farbe. BUY/COVER gruen, SELL/SHORT rot, HOLD grau-blau, NONE grau.
export function verdictToVisual(v: LongVerdict | ShortVerdict): { label: string; colorClass: string } {
  switch (v) {
    case "BUY":
    case "COVER": return { label: v, colorClass: "text-green-600" };
    case "SELL":
    case "SHORT": return { label: v, colorClass: "text-red-600" };
    case "HOLD":  return { label: v, colorClass: "text-slate-500" };
    case "NONE":  return { label: v, colorClass: "text-slate-400" };
  }
}
```

- [ ] **Step 4: Test grün + Commit**

Run: `cd frontend && npx vitest run src/lib/judgment.test.ts` → PASS.
```bash
git add frontend/src/lib/judgment.ts frontend/src/lib/judgment.test.ts
git commit -m "feat(frontend): pure confidenceFlags/consistencyHint/verdictToVisual (Urteils-Logik)"
```

---

## Task 5: Pure Anzeige-Logik — Futures (Roll-Yield, Hebel) + Zinskurve + Anomalie

**Files:**
- Create: `frontend/src/lib/futures.ts`, `frontend/src/lib/curve.ts`, `frontend/src/lib/anomaly.ts`
- Test: `frontend/src/lib/futures.test.ts`, `frontend/src/lib/curve.test.ts`, `frontend/src/lib/anomaly.test.ts`

**Interfaces:**
- Consumes: `AnomalySeverity` (Task 2).
- Produces (`futures.ts`): `type CurveForm = "contango" | "backwardation" | "flat"`; `rollYieldVisual(annualPct: number, form: CurveForm): { label: string; colorClass: string; arrow: string }`; `leverageFactor(notional: number, margin: number): number`.
- Produces (`curve.ts`): `interface SpreadStatus { value: number; inverted: boolean }`; `yieldSpreadStatus(spread: number): SpreadStatus` (invertiert wenn < 0).
- Produces (`anomaly.ts`): `zScoreFlag(z: number): "none" | "watch" | "anomaly"` (|z|≥1.5 watch, |z|>2.0 anomaly); `anomalySeverityToVisual(s: AnomalySeverity): { label: string; colorClass: string }`.

- [ ] **Step 1: Failing-Tests**

`frontend/src/lib/futures.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { rollYieldVisual, leverageFactor } from "./futures";

describe("rollYieldVisual", () => {
  it("Contango => Gegenwind, negativ, Abwaerts-Pfeil (Roll-Yield<0)", () => {
    const v = rollYieldVisual(-3.1, "contango");
    expect(v.arrow).toBe("▼");
    expect(v.colorClass).toContain("red");
    expect(v.label).toMatch(/Gegenwind/i);
  });
  it("Backwardation => Rueckenwind, positiv, Aufwaerts-Pfeil", () => {
    const v = rollYieldVisual(2.4, "backwardation");
    expect(v.arrow).toBe("▲");
    expect(v.colorClass).toContain("green");
    expect(v.label).toMatch(/Rueckenwind|Rückenwind/i);
  });
});

describe("leverageFactor", () => {
  it("Hebel = Nominalwert / Margin", () => {
    expect(leverageFactor(236000, 7150)).toBeCloseTo(33.0, 0);
  });
  it("Margin 0 => 0 (kein Division-durch-Null-Absturz)", () => {
    expect(leverageFactor(1000, 0)).toBe(0);
  });
});
```

`frontend/src/lib/curve.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { yieldSpreadStatus } from "./curve";

describe("yieldSpreadStatus", () => {
  it("negativer Spread = invertiert (Rezessions-FrUehsignal)", () => {
    expect(yieldSpreadStatus(-0.2)).toEqual({ value: -0.2, inverted: true });
  });
  it("positiver/Null-Spread = nicht invertiert", () => {
    expect(yieldSpreadStatus(0.4)).toEqual({ value: 0.4, inverted: false });
    expect(yieldSpreadStatus(0)).toEqual({ value: 0, inverted: false });
  });
});
```

`frontend/src/lib/anomaly.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { zScoreFlag, anomalySeverityToVisual } from "./anomaly";

describe("zScoreFlag", () => {
  it("|z|>2.0 => anomaly, |z|>=1.5 => watch, sonst none", () => {
    expect(zScoreFlag(2.1)).toBe("anomaly");
    expect(zScoreFlag(-2.1)).toBe("anomaly");
    expect(zScoreFlag(1.5)).toBe("watch");
    expect(zScoreFlag(-1.6)).toBe("watch");
    expect(zScoreFlag(0.9)).toBe("none");
  });
});

describe("anomalySeverityToVisual", () => {
  it("Schwere -> Label + Farbe", () => {
    expect(anomalySeverityToVisual("high").colorClass).toContain("red");
    expect(anomalySeverityToVisual("none").colorClass).toContain("slate");
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/lib/futures.test.ts src/lib/curve.test.ts src/lib/anomaly.test.ts` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/lib/futures.ts`:
```ts
export type CurveForm = "contango" | "backwardation" | "flat";

// Roll-Yield: Contango (Terminpreis > Spot) => negativ (Halten kostet, Gegenwind);
// Backwardation => positiv (Rueckenwind). Vorzeichen/Richtung benannt, nicht nur Farbe
// (AGENTS.md §3, Konzept §5.1).
export function rollYieldVisual(
  annualPct: number,
  _form: CurveForm,
): { label: string; colorClass: string; arrow: string } {
  if (annualPct < 0) return { label: "Gegenwind (Contango)", colorClass: "text-red-600", arrow: "▼" };
  if (annualPct > 0) return { label: "Rückenwind (Backwardation)", colorClass: "text-green-600", arrow: "▲" };
  return { label: "neutral", colorClass: "text-slate-500", arrow: "→" };
}

// Hebel = Nominalwert / Margin (wahres Risiko, nicht Nominalwert). Margin<=0 => 0 (defensiv).
export function leverageFactor(notional: number, margin: number): number {
  if (margin <= 0) return 0;
  return notional / margin;
}
```

`frontend/src/lib/curve.ts`:
```ts
export interface SpreadStatus {
  value: number;
  inverted: boolean;
}

// Zinskurven-Spread (z. B. 10J-2J): negativ = invertiert = klassisches Rezessions-
// Fruehsignal. Richtung explizit (AGENTS.md §3).
export function yieldSpreadStatus(spread: number): SpreadStatus {
  return { value: spread, inverted: spread < 0 };
}
```

`frontend/src/lib/anomaly.ts`:
```ts
import type { AnomalySeverity } from "../contract/common";

// Z-Score-Auffaelligkeit (frontend_notes.md): |Z|>2.0 = Anomalie, |Z|>=1.5 = auffaellig (watch).
export function zScoreFlag(z: number): "none" | "watch" | "anomaly" {
  const a = Math.abs(z);
  if (a > 2.0) return "anomaly";
  if (a >= 1.5) return "watch";
  return "none";
}

export function anomalySeverityToVisual(s: AnomalySeverity): { label: string; colorClass: string } {
  switch (s) {
    case "high":   return { label: "hoch",   colorClass: "text-red-600" };
    case "medium": return { label: "mittel", colorClass: "text-amber-600" };
    case "low":    return { label: "gering", colorClass: "text-yellow-600" };
    case "none":   return { label: "keine",  colorClass: "text-slate-400" };
  }
}
```

- [ ] **Step 4: Tests grün + Commit**

Run: `cd frontend && npx vitest run src/lib/futures.test.ts src/lib/curve.test.ts src/lib/anomaly.test.ts` → PASS.
```bash
git add frontend/src/lib/futures.ts frontend/src/lib/futures.test.ts frontend/src/lib/curve.ts frontend/src/lib/curve.test.ts frontend/src/lib/anomaly.ts frontend/src/lib/anomaly.test.ts
git commit -m "feat(frontend): pure Roll-Yield/Hebel/Zinskurven-Spread/Anomalie-Logik (fachliche Schwellen)"
```

---

## Task 6: DemoBadge + UnderlyingWrapperBadge + ThresholdBadges

**Files:**
- Create: `frontend/src/components/DemoBadge.tsx`, `UnderlyingWrapperBadge.tsx`, `ThresholdBadges.tsx`
- Test: zugehörige `.test.tsx`

**Interfaces:**
- Consumes: `underlyingToVisual`/`wrapperToVisual` (Task 3), `confidenceFlags` (Task 4), `Underlying`/`Wrapper` (Task 2).
- Produces: `DemoBadge({ isDemo }: { isDemo: boolean })` (rendert nichts bei `false`); `UnderlyingWrapperBadge({ underlying, wrapper }: { underlying: Underlying; wrapper: Wrapper })`; `AutoHoldBadge`/`CashBiasBadge` als `({ confidence }: { confidence: number })` (rendern nur, wenn das jeweilige Flag gesetzt ist).

- [ ] **Step 1: Failing-Tests**

`frontend/src/components/DemoBadge.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DemoBadge } from "./DemoBadge";

describe("DemoBadge", () => {
  it("zeigt 'Demo-Daten' bei isDemo=true", () => {
    render(<DemoBadge isDemo />);
    expect(screen.getByText(/Demo-Daten/i)).toBeInTheDocument();
  });
  it("rendert nichts bei isDemo=false (verschwindet beim Umstieg automatisch)", () => {
    const { container } = render(<DemoBadge isDemo={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

`frontend/src/components/UnderlyingWrapperBadge.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UnderlyingWrapperBadge } from "./UnderlyingWrapperBadge";

describe("UnderlyingWrapperBadge", () => {
  it("zeigt beide Etiketten", () => {
    render(<UnderlyingWrapperBadge underlying="precious_metal" wrapper="future" />);
    expect(screen.getByText(/Edelmetall/)).toBeInTheDocument();
    expect(screen.getByText(/Future/)).toBeInTheDocument();
  });
});
```

`frontend/src/components/ThresholdBadges.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutoHoldBadge, CashBiasBadge } from "./ThresholdBadges";

describe("Schwellen-Badges", () => {
  it("AutoHoldBadge erscheint unter 0.50, nicht darueber", () => {
    const { rerender, container } = render(<AutoHoldBadge confidence={0.49} />);
    expect(screen.getByText(/auto-HOLD/i)).toBeInTheDocument();
    rerender(<AutoHoldBadge confidence={0.6} />);
    expect(container).toBeEmptyDOMElement();
  });
  it("CashBiasBadge erscheint unter 0.35", () => {
    render(<CashBiasBadge confidence={0.30} />);
    expect(screen.getByText(/Cash-Bias/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/components/DemoBadge.test.tsx src/components/UnderlyingWrapperBadge.test.tsx src/components/ThresholdBadges.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/components/DemoBadge.tsx`:
```tsx
// Markiert eine Ansicht als aus Beispielwerten gespeist. Bei isDemo=false rendert es
// nichts -> beim Umstieg auf echte Daten verschwindet das Etikett automatisch (Spec §2.2).
export function DemoBadge({ isDemo }: { isDemo: boolean }) {
  if (!isDemo) return null;
  return (
    <span
      title="Diese Ansicht zeigt Demo-Daten, weil der echte Backend-Endpunkt noch fehlt."
      className="inline-block rounded bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700"
    >
      Demo-Daten
    </span>
  );
}
```

`frontend/src/components/UnderlyingWrapperBadge.tsx`:
```tsx
import type { Underlying, Wrapper } from "../contract/common";
import { underlyingToVisual, wrapperToVisual } from "../lib/assets";

// Zwei farbcodierte Etiketten (Konzept §5.2): Basiswert x Huelle.
export function UnderlyingWrapperBadge({ underlying, wrapper }: { underlying: Underlying; wrapper: Wrapper }) {
  const u = underlyingToVisual(underlying);
  const w = wrapperToVisual(wrapper);
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${u.colorClass}`}>
        <span aria-hidden>{u.icon}</span>{u.label}
      </span>
      <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${w.colorClass}`}>
        <span aria-hidden>{w.icon}</span>{w.label}
      </span>
    </span>
  );
}
```

`frontend/src/components/ThresholdBadges.tsx`:
```tsx
import { confidenceFlags } from "../lib/judgment";

// Konfidenz <0.50 -> auto-HOLD (Konzept §2.3 / frontend_notes.md).
export function AutoHoldBadge({ confidence }: { confidence: number }) {
  if (!confidenceFlags(confidence).autoHold) return null;
  return (
    <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
      ⚠ &lt;0.50 → auto-HOLD
    </span>
  );
}

// Konfidenz <0.35 -> zusaetzlich Cash-Bias.
export function CashBiasBadge({ confidence }: { confidence: number }) {
  if (!confidenceFlags(confidence).cashBias) return null;
  return (
    <span className="inline-block rounded bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
      &lt;0.35 → Cash-Bias
    </span>
  );
}
```

- [ ] **Step 4: Tests grün + Commit**

Run: `cd frontend && npx vitest run src/components/DemoBadge.test.tsx src/components/UnderlyingWrapperBadge.test.tsx src/components/ThresholdBadges.test.tsx` → PASS.
```bash
git add frontend/src/components/DemoBadge.tsx frontend/src/components/DemoBadge.test.tsx frontend/src/components/UnderlyingWrapperBadge.tsx frontend/src/components/UnderlyingWrapperBadge.test.tsx frontend/src/components/ThresholdBadges.tsx frontend/src/components/ThresholdBadges.test.tsx
git commit -m "feat(frontend): DemoBadge + UnderlyingWrapperBadge + Schwellen-Badges"
```

---

## Task 7: XaiPanel + LongShortPanel + AnomalyReport + SourceHealth

**Files:**
- Create: `frontend/src/components/XaiPanel.tsx`, `LongShortPanel.tsx`, `AnomalyReport.tsx`, `SourceHealth.tsx`
- Test: zugehörige `.test.tsx`

**Interfaces:**
- Consumes: `ConfidenceBar` (bestehend), `verdictToVisual`/`consistencyHint` (Task 4), `AutoHoldBadge`/`CashBiasBadge` (Task 6), `anomalySeverityToVisual` (Task 5), `sourcesLabel` (bestehend in `lib/display.ts`), `LongVerdict`/`ShortVerdict`/`AnomalySeverity` (Task 2).
- Produces:
  - `interface XaiDriver { text: string; sign: "+" | "-" }`; `interface XaiContent { drivers: XaiDriver[]; conflicts: string[]; confidenceReason: string; whatFlips: string }`; `XaiPanel({ xai }: { xai: XaiContent })` (aufklappbar, Default eingeklappt).
  - `interface VerdictLens { verdict: LongVerdict | ShortVerdict; confidence: number; rationale: string; xai?: XaiContent }`; `LongShortPanel({ long, short }: { long: VerdictLens; short: VerdictLens })`.
  - `interface AnomalyContent { severity: AnomalySeverity; outliers: string[]; conflicts: string[] }`; `AnomalyReport({ anomaly }: { anomaly: AnomalyContent })`.
  - `interface FailedSource { key: string; reason: string }`; `SourceHealth({ active, total, failed }: { active: number; total: number; failed?: FailedSource[] })`.

- [ ] **Step 1: Failing-Tests**

`frontend/src/components/XaiPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { XaiPanel } from "./XaiPanel";

const xai = {
  drivers: [{ text: "Makro stützt", sign: "+" as const }, { text: "Contango bremst", sign: "-" as const }],
  conflicts: ["Top-Down bullish vs. Roll-Struktur bearish"],
  confidenceReason: "2 starke Gegensignale + 1 Quelle UNAVAILABLE",
  whatFlips: "Wechsel in Backwardation ODER Realzins ↓",
};

describe("XaiPanel", () => {
  it("zeigt nach dem Aufklappen Treiber, Widersprueche und 'was kippt'", async () => {
    render(<XaiPanel xai={xai} />);
    await userEvent.click(screen.getByRole("button", { name: /XAI/i }));
    expect(screen.getByText(/Makro stützt/)).toBeInTheDocument();
    expect(screen.getByText(/Top-Down bullish/)).toBeInTheDocument();
    expect(screen.getByText(/Backwardation/)).toBeInTheDocument();
  });
});
```

`frontend/src/components/LongShortPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LongShortPanel } from "./LongShortPanel";

describe("LongShortPanel", () => {
  it("zeigt beide Linsen gleichwertig nebeneinander + Konfidenz-%", () => {
    render(
      <LongShortPanel
        long={{ verdict: "HOLD", confidence: 0.47, rationale: "Roll-Gegenwind" }}
        short={{ verdict: "NONE", confidence: 0.22, rationale: "kein Short" }}
      />,
    );
    expect(screen.getByText("LONG-LINSE")).toBeInTheDocument();
    expect(screen.getByText("SHORT-LINSE")).toBeInTheDocument();
    expect(screen.getByText("47 %")).toBeInTheDocument();
    expect(screen.getByText("22 %")).toBeInTheDocument();
  });
  it("zeigt das auto-HOLD-Flag unter 0.50", () => {
    render(
      <LongShortPanel
        long={{ verdict: "HOLD", confidence: 0.47, rationale: "x" }}
        short={{ verdict: "NONE", confidence: 0.22, rationale: "y" }}
      />,
    );
    expect(screen.getByText(/auto-HOLD/i)).toBeInTheDocument();
  });
});
```

`frontend/src/components/AnomalyReport.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnomalyReport } from "./AnomalyReport";

describe("AnomalyReport", () => {
  it("zeigt Schwere und Ausreisser/Widersprueche getrennt", () => {
    render(<AnomalyReport anomaly={{ severity: "high", outliers: ["KGV |Z|=2.3"], conflicts: ["Top-Down vs Bottom-Up"] }} />);
    expect(screen.getByText(/hoch/i)).toBeInTheDocument();
    expect(screen.getByText(/KGV/)).toBeInTheDocument();
    expect(screen.getByText(/Top-Down vs Bottom-Up/)).toBeInTheDocument();
  });
});
```

`frontend/src/components/SourceHealth.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SourceHealth } from "./SourceHealth";

describe("SourceHealth", () => {
  it("zeigt x/y aktiv und listet ausgefallene Quellen nach Klick", async () => {
    render(<SourceHealth active={4} total={5} failed={[{ key: "Sektoren", reason: "Stub" }]} />);
    expect(screen.getByText("4/5 Quellen aktiv")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/Sektoren/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/components/XaiPanel.test.tsx src/components/LongShortPanel.test.tsx src/components/AnomalyReport.test.tsx src/components/SourceHealth.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/components/XaiPanel.tsx`:
```tsx
import { useState } from "react";

export interface XaiDriver { text: string; sign: "+" | "-"; }
export interface XaiContent {
  drivers: XaiDriver[];
  conflicts: string[];
  confidenceReason: string;
  whatFlips: string;
}

// Aufklappbares XAI-Panel (Konzept §4.6): die vier Fragen — Treiber (+/-),
// Widersprueche, warum diese Konfidenz, was kippt es.
export function XaiPanel({ xai }: { xai: XaiContent }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded border border-slate-200 dark:border-slate-700">
      <button type="button" onClick={() => setOpen((o) => !o)} className="w-full px-3 py-2 text-left text-sm font-medium">
        XAI — Begründung {open ? "▾" : "▸"}
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3 text-sm">
          <div>
            <div className="text-xs uppercase text-slate-500">Entscheidende Signale</div>
            <ul>
              {xai.drivers.map((d, i) => (
                <li key={i} className={d.sign === "+" ? "text-green-600" : "text-red-600"}>
                  {d.sign === "+" ? "＋" : "－"} {d.text}
                </li>
              ))}
            </ul>
          </div>
          <div><span className="text-xs uppercase text-slate-500">Widersprüche: </span>{xai.conflicts.join("; ") || "—"}</div>
          <div><span className="text-xs uppercase text-slate-500">Konfidenz-Begründung: </span>{xai.confidenceReason}</div>
          <div><span className="text-xs uppercase text-slate-500">Was es kippen würde: </span>{xai.whatFlips}</div>
        </div>
      )}
    </div>
  );
}
```

`frontend/src/components/LongShortPanel.tsx`:
```tsx
import { ConfidenceBar } from "./ConfidenceBar";
import { AutoHoldBadge, CashBiasBadge } from "./ThresholdBadges";
import { XaiPanel, type XaiContent } from "./XaiPanel";
import { verdictToVisual, consistencyHint } from "../lib/judgment";
import type { LongVerdict, ShortVerdict } from "../contract/common";

export interface VerdictLens {
  verdict: LongVerdict | ShortVerdict;
  confidence: number;
  rationale: string;
  xai?: XaiContent;
}

function Lens({ title, lens }: { title: string; lens: VerdictLens }) {
  const v = verdictToVisual(lens.verdict);
  return (
    <div className="flex-1 space-y-2 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-500">{title}</div>
      <div className={`text-xl font-bold ${v.colorClass}`}>▶ {v.label}</div>
      <ConfidenceBar value={lens.confidence} />
      <div className="flex flex-wrap gap-1">
        <AutoHoldBadge confidence={lens.confidence} />
        <CashBiasBadge confidence={lens.confidence} />
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">{lens.rationale}</p>
      {lens.xai && <XaiPanel xai={lens.xai} />}
    </div>
  );
}

// Long und Short STRIKT gleichwertig nebeneinander, nie ein Umschalter (Konzept §5.3).
export function LongShortPanel({ long, short }: { long: VerdictLens; short: VerdictLens }) {
  const hint = consistencyHint(long.verdict as LongVerdict, short.verdict as ShortVerdict);
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700">
      <div className="flex divide-x divide-slate-200 dark:divide-slate-700">
        <Lens title="LONG-LINSE" lens={long} />
        <Lens title="SHORT-LINSE" lens={short} />
      </div>
      {hint && <div className="border-t border-slate-200 px-3 py-1.5 text-sm text-slate-600 dark:border-slate-700">{hint}</div>}
    </div>
  );
}
```

`frontend/src/components/AnomalyReport.tsx`:
```tsx
import { anomalySeverityToVisual } from "../lib/anomaly";
import type { AnomalySeverity } from "../contract/common";

export interface AnomalyContent {
  severity: AnomalySeverity;
  outliers: string[];   // statistische Ausreisser |Z|>2.0
  conflicts: string[];  // Signalwidersprueche (Top-Down vs Bottom-Up)
}

// Getrennt: statistische Ausreisser vs. Signalwidersprueche (frontend_notes.md / Konzept §2.3).
export function AnomalyReport({ anomaly }: { anomaly: AnomalyContent }) {
  const v = anomalySeverityToVisual(anomaly.severity);
  return (
    <div className="rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
      <div>Anomalie-Schwere: <span className={`font-semibold ${v.colorClass}`}>{v.label}</span></div>
      <div className="mt-1"><span className="text-xs uppercase text-slate-500">Statistische Ausreißer: </span>{anomaly.outliers.join("; ") || "—"}</div>
      <div><span className="text-xs uppercase text-slate-500">Signalwidersprüche: </span>{anomaly.conflicts.join("; ") || "—"}</div>
    </div>
  );
}
```

`frontend/src/components/SourceHealth.tsx`:
```tsx
import { useState } from "react";
import { sourcesLabel } from "../lib/display";

export interface FailedSource { key: string; reason: string; }

// Verallgemeinerter Daten-Health-Zaehler (Konzept §5.4): x/y aktiv, Klick listet Ausfaelle.
export function SourceHealth({ active, total, failed = [] }: { active: number; total: number; failed?: FailedSource[] }) {
  const [open, setOpen] = useState(false);
  const allUp = active === total;
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`text-sm ${allUp ? "text-slate-500" : "text-amber-600"}`}
      >
        {sourcesLabel(active, total)}{failed.length > 0 ? " ⚠" : ""}
      </button>
      {open && failed.length > 0 && (
        <ul className="absolute z-10 mt-1 rounded border border-slate-200 bg-white p-2 text-xs shadow dark:border-slate-700 dark:bg-slate-800">
          {failed.map((f) => (
            <li key={f.key}>{f.key}: {f.reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Tests grün + Commit**

Run: `cd frontend && npx vitest run src/components/XaiPanel.test.tsx src/components/LongShortPanel.test.tsx src/components/AnomalyReport.test.tsx src/components/SourceHealth.test.tsx` → PASS.
```bash
git add frontend/src/components/XaiPanel.tsx frontend/src/components/XaiPanel.test.tsx frontend/src/components/LongShortPanel.tsx frontend/src/components/LongShortPanel.test.tsx frontend/src/components/AnomalyReport.tsx frontend/src/components/AnomalyReport.test.tsx frontend/src/components/SourceHealth.tsx frontend/src/components/SourceHealth.test.tsx
git commit -m "feat(frontend): XaiPanel + LongShortPanel + AnomalyReport + SourceHealth (Komponenten-Bibliothek)"
```

---

## Task 8: ECharts-Referenz-Wrapper (ChartContainer + LineCurve)

**Files:**
- Create: `frontend/src/components/charts/ChartContainer.tsx`, `frontend/src/components/charts/LineCurve.tsx`
- Test: `frontend/src/components/charts/LineCurve.test.tsx`

**Interfaces:**
- Produces: `interface LinePoint { x: string; y: number }`; `interface LineSeries { name: string; points: LinePoint[] }`; `LineCurve({ series, height }: { series: LineSeries[]; height?: number })`. `ChartContainer` kapselt das lazy-geladene `ReactECharts` und reicht `option` durch.

> **Testbarkeit:** ECharts wird im Test gemockt (kein Canvas in jsdom). Der Test prüft, dass aus `series` eine ECharts-`option` mit korrekten Serien gebaut wird — die pure `buildLineOption`-Funktion wird exportiert und direkt getestet.

- [ ] **Step 1: Failing-Test (pure option-Builder)**

`frontend/src/components/charts/LineCurve.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";

// ECharts in jsdom mocken (kein Canvas).
vi.mock("echarts-for-react", () => ({ default: () => null }));

import { buildLineOption } from "./LineCurve";

describe("buildLineOption", () => {
  it("baut x-Achsen-Kategorien und eine Serie je LineSeries", () => {
    const opt = buildLineOption([
      { name: "Rendite", points: [{ x: "3M", y: 2 }, { x: "2J", y: 3 }] },
    ]);
    expect(opt.xAxis.data).toEqual(["3M", "2J"]);
    expect(opt.series).toHaveLength(1);
    expect(opt.series[0]).toMatchObject({ name: "Rendite", type: "line", data: [2, 3] });
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/components/charts/LineCurve.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/components/charts/ChartContainer.tsx`:
```tsx
import { lazy, Suspense } from "react";

// ReactECharts lazy laden -> eigener Chunk, schlankes Grund-Bundle (Spec §5).
const ReactECharts = lazy(() => import("echarts-for-react"));

export function ChartContainer({ option, height = 280 }: { option: object; height?: number }) {
  return (
    <Suspense fallback={<div className="text-sm text-slate-500">Diagramm lädt …</div>}>
      <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />
    </Suspense>
  );
}
```

`frontend/src/components/charts/LineCurve.tsx`:
```tsx
import { ChartContainer } from "./ChartContainer";

export interface LinePoint { x: string; y: number; }
export interface LineSeries { name: string; points: LinePoint[]; }

// Pure: baut die ECharts-option aus den Serien (separat testbar, ohne Canvas).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildLineOption(series: LineSeries[]): any {
  const categories = series[0]?.points.map((p) => p.x) ?? [];
  return {
    tooltip: { trigger: "axis" },
    legend: { show: series.length > 1 },
    xAxis: { type: "category", data: categories },
    yAxis: { type: "value" },
    series: series.map((s) => ({ name: s.name, type: "line", smooth: true, data: s.points.map((p) => p.y) })),
  };
}

export function LineCurve({ series, height }: { series: LineSeries[]; height?: number }) {
  return <ChartContainer option={buildLineOption(series)} height={height} />;
}
```

- [ ] **Step 4: Test grün + Commit**

Run: `cd frontend && npx vitest run src/components/charts/LineCurve.test.tsx` → PASS.
```bash
git add frontend/src/components/charts
git commit -m "feat(frontend): ECharts-Referenz-Wrapper (ChartContainer + LineCurve, pure option-Builder)"
```

---

## Task 9: Theme-Hook (hell/dunkel)

**Files:**
- Create: `frontend/src/shell/useTheme.ts`
- Test: `frontend/src/shell/useTheme.test.tsx`

**Interfaces:**
- Produces: `type Theme = "light" | "dark"`; `useTheme(): { theme: Theme; toggle: () => void }`. Setzt/entfernt die Klasse `dark` auf `document.documentElement` und persistiert unter `aaia_theme`.

- [ ] **Step 1: Failing-Test**

`frontend/src/shell/useTheme.test.tsx`:
```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "./useTheme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
});

describe("useTheme", () => {
  it("schaltet zwischen hell und dunkel und setzt die 'dark'-Klasse", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
    act(() => result.current.toggle());
    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("aaia_theme")).toBe("dark");
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/shell/useTheme.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/shell/useTheme.ts`:
```ts
import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "aaia_theme";

// Hell/Dunkel-Umschalter; persistiert und steuert die Tailwind-'dark'-Klasse am <html>.
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(KEY) as Theme) || "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), []);
  return { theme, toggle };
}
```

- [ ] **Step 4: Test grün + Commit**

Run: `cd frontend && npx vitest run src/shell/useTheme.test.tsx` → PASS.
```bash
git add frontend/src/shell/useTheme.ts frontend/src/shell/useTheme.test.tsx
git commit -m "feat(frontend): useTheme (hell/dunkel, persistiert)"
```

---

## Task 10: Shell — Sidebar + Topbar + AppShell

**Files:**
- Create: `frontend/src/shell/Sidebar.tsx`, `frontend/src/shell/Topbar.tsx`, `frontend/src/shell/AppShell.tsx`, `frontend/src/pages/PlaceholderPage.tsx`
- Test: `frontend/src/shell/Sidebar.test.tsx`, `frontend/src/shell/Topbar.test.tsx`, `frontend/src/shell/AppShell.test.tsx`

**Interfaces:**
- Consumes: `react-router-dom` (`NavLink`, `Outlet`, `useNavigate`), `useTheme` (Task 9), `SourceHealth` (Task 7).
- Produces:
  - `Sidebar()` — `NavLink`s zu `/cockpit`, `/deep-dive`, `/portfolio`, `/inbox`, `/backtester`, `/einstellungen`; aktiver Link hervorgehoben.
  - `interface TopbarProps { inboxCount: number; onSearch: (ticker: string) => void; onLogout?: () => void }`; `Topbar(props)`.
  - `interface AppShellProps { inboxCount: number; onLogout?: () => void }`; `AppShell(props)` — Layout (Sidebar links, Topbar oben, `<Outlet/>` für den Inhalt).
  - `PlaceholderPage({ title }: { title: string })` — „… (in Arbeit)".

> Tests laufen mit `<MemoryRouter>` als Wrapper, da `NavLink`/`Outlet` einen Router-Kontext brauchen.

- [ ] **Step 1: Failing-Tests**

`frontend/src/shell/Sidebar.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("zeigt alle fuenf Hauptbereiche + Einstellungen", () => {
    render(<MemoryRouter><Sidebar /></MemoryRouter>);
    for (const label of ["Cockpit", "Deep-Dive", "Portfolio", "Inbox", "Backtester", "Einstellungen"]) {
      expect(screen.getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });
});
```

`frontend/src/shell/Topbar.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  it("zeigt den Inbox-Badge mit Anzahl", () => {
    render(<MemoryRouter><Topbar inboxCount={3} onSearch={() => {}} /></MemoryRouter>);
    expect(screen.getByText("3")).toBeInTheDocument();
  });
  it("ruft onSearch mit dem eingegebenen Ticker", async () => {
    const onSearch = vi.fn();
    render(<MemoryRouter><Topbar inboxCount={0} onSearch={onSearch} /></MemoryRouter>);
    await userEvent.type(screen.getByPlaceholderText(/Ticker/i), "AAPL{enter}");
    expect(onSearch).toHaveBeenCalledWith("AAPL");
  });
});
```

`frontend/src/shell/AppShell.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("rendert die Shell + den Outlet-Inhalt der aktiven Route", () => {
    render(
      <MemoryRouter initialEntries={["/cockpit"]}>
        <Routes>
          <Route element={<AppShell inboxCount={0} />}>
            <Route path="/cockpit" element={<div>COCKPIT-INHALT</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("COCKPIT-INHALT")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Portfolio/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Tests laufen lassen — müssen fehlschlagen**

Run: `cd frontend && npx vitest run src/shell/Sidebar.test.tsx src/shell/Topbar.test.tsx src/shell/AppShell.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/pages/PlaceholderPage.tsx`:
```tsx
// Generische Platzhalter-Seite fuer Bereiche, die spaetere Slices fuellen.
export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500 dark:border-slate-700">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm">Dieser Bereich wird in einem folgenden Slice gebaut.</p>
    </div>
  );
}
```

`frontend/src/shell/Sidebar.tsx`:
```tsx
import { NavLink } from "react-router-dom";

const ITEMS: { to: string; label: string; icon: string }[] = [
  { to: "/cockpit", label: "Cockpit", icon: "▣" },
  { to: "/deep-dive", label: "Deep-Dive", icon: "◆" },
  { to: "/portfolio", label: "Portfolio", icon: "⬚" },
  { to: "/inbox", label: "Inbox", icon: "✉" },
  { to: "/backtester", label: "Backtester", icon: "↺" },
  { to: "/einstellungen", label: "Einstellungen", icon: "⚙" },
];

export function Sidebar() {
  return (
    <nav className="flex w-48 shrink-0 flex-col gap-1 border-r border-slate-200 p-3 dark:border-slate-700">
      <div className="px-2 pb-2 text-lg font-bold">AAIA</div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded px-2 py-1.5 text-sm ${
              isActive ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            }`
          }
        >
          <span aria-hidden>{it.icon}</span>{it.label}
        </NavLink>
      ))}
    </nav>
  );
}
```

`frontend/src/shell/Topbar.tsx`:
```tsx
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTheme } from "./useTheme";

export interface TopbarProps {
  inboxCount: number;
  onSearch: (ticker: string) => void;
  onLogout?: () => void;
}

export function Topbar({ inboxCount, onSearch, onLogout }: TopbarProps) {
  const { theme, toggle } = useTheme();
  const [q, setQ] = useState("");
  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-4 py-2 dark:border-slate-700">
      <form
        onSubmit={(e) => { e.preventDefault(); const t = q.trim().toUpperCase(); if (t) onSearch(t); }}
        className="flex-1"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="🔍 Ticker/Markt suchen …"
          aria-label="Ticker/Markt suchen"
          className="w-full max-w-md rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </form>
      <div className="flex items-center gap-3">
        <NavLink to="/inbox" className="relative text-sm" aria-label="Inbox">
          ✉
          {inboxCount > 0 && (
            <span className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{inboxCount}</span>
          )}
        </NavLink>
        <button type="button" onClick={toggle} className="text-sm" aria-label="Theme umschalten">
          {theme === "dark" ? "☀" : "◐"}
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout} className="text-sm text-slate-500 underline">Abmelden</button>
        )}
      </div>
    </header>
  );
}
```

`frontend/src/shell/AppShell.tsx`:
```tsx
import { Outlet, useNavigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export interface AppShellProps {
  inboxCount: number;
  onLogout?: () => void;
}

export function AppShell({ inboxCount, onLogout }: AppShellProps) {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar inboxCount={inboxCount} onSearch={(t) => navigate(`/deep-dive/${t}`)} onLogout={onLogout} />
        <main className="min-w-0 flex-1 space-y-4 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Tests grün + Commit**

Run: `cd frontend && npx vitest run src/shell/Sidebar.test.tsx src/shell/Topbar.test.tsx src/shell/AppShell.test.tsx` → PASS.
```bash
git add frontend/src/shell frontend/src/pages/PlaceholderPage.tsx
git commit -m "feat(frontend): App-Shell (Sidebar + Topbar mit Suche/Inbox-Badge/Theme/Logout + AppShell)"
```

---

## Task 11: Router + App-Einbindung (Cockpit in der Shell)

**Files:**
- Create: `frontend/src/routes.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/pages/CockpitPage.tsx` (Header-Doppelung entfernen, da Topbar nun global)
- Test: `frontend/src/routes.test.tsx`

**Interfaces:**
- Consumes: `createBrowserRouter`/`RouterProvider` (oder `BrowserRouter`+`Routes`), `AppShell` (Task 10), `CockpitPage` (bestehend), `PlaceholderPage` (Task 10), `useAuth`/`LoginGate` (bestehend).
- Produces: `AppRoutes({ onLogout }: { onLogout?: () => void })` — Routen unter der `AppShell`: `/cockpit` (+ Default-Redirect von `/`), `/deep-dive`, `/deep-dive/:ticker`, `/portfolio`, `/inbox`, `/backtester`, `/einstellungen`. Die noch leeren Bereiche rendern `PlaceholderPage`.

> **Cockpit-Anpassung:** Die heutige `CockpitPage` hat einen eigenen `<header>` mit Titel/Logout/Run/Health. Da die Topbar diese global stellt, wird der Seiten-Header der `CockpitPage` auf die cockpit-spezifischen Teile reduziert (Überschrift „Cockpit — Übersicht", Run-Button, Health), Logout entfällt dort (jetzt in der Topbar). Die `deps`/Live-Anbindung bleibt unverändert.

- [ ] **Step 1: Failing-Test**

`frontend/src/routes.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./routes";

// Cockpit-Datenhook neutralisieren (kein echter Netz-Call im Routing-Test).
vi.mock("./hooks/useCockpit", () => ({
  useCockpit: () => ({ overview: null, phase: "ready", error: null, events: [], startAnalysis: () => {} }),
}));

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>);
}

describe("AppRoutes", () => {
  it("zeigt Portfolio-Platzhalter unter /portfolio", () => {
    renderAt("/portfolio");
    expect(screen.getByText(/Portfolio/i)).toBeInTheDocument();
    expect(screen.getByText(/in einem folgenden Slice/i)).toBeInTheDocument();
  });
  it("leitet / auf das Cockpit", () => {
    renderAt("/");
    expect(screen.getByText(/Cockpit/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd frontend && npx vitest run src/routes.test.tsx` → FAIL.

- [ ] **Step 3: Implementieren**

`frontend/src/routes.tsx`:
```tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./shell/AppShell";
import { CockpitPage } from "./pages/CockpitPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import type { UseCockpitDeps } from "./hooks/useCockpit";

// Routen unter der Shell. Inbox-Anzahl ist in Slice 0 noch 0 (Slice 4 speist sie).
export function AppRoutes({ deps, onLogout }: { deps?: UseCockpitDeps; onLogout?: () => void }) {
  return (
    <Routes>
      <Route element={<AppShell inboxCount={0} onLogout={onLogout} />}>
        <Route index element={<Navigate to="/cockpit" replace />} />
        <Route path="/cockpit" element={<CockpitPage deps={deps} />} />
        <Route path="/deep-dive" element={<PlaceholderPage title="Deep-Dive — Titel über die Suche oben öffnen" />} />
        <Route path="/deep-dive/:ticker" element={<PlaceholderPage title="Deep-Dive" />} />
        <Route path="/portfolio" element={<PlaceholderPage title="Portfolio" />} />
        <Route path="/inbox" element={<PlaceholderPage title="Inbox" />} />
        <Route path="/backtester" element={<PlaceholderPage title="Backtester" />} />
        <Route path="/einstellungen" element={<PlaceholderPage title="Einstellungen" />} />
        <Route path="*" element={<Navigate to="/cockpit" replace />} />
      </Route>
    </Routes>
  );
}
```

`frontend/src/App.tsx` (gesamten Inhalt ersetzen):
```tsx
import { useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { useAuth } from "./auth/useAuth";
import { LoginGate } from "./auth/LoginGate";
import { AppRoutes } from "./routes";

export default function App() {
  const { token, login, logout } = useAuth();
  const [authError, setAuthError] = useState(false);

  if (!token) {
    return <LoginGate error={authError} onSubmit={(t) => { setAuthError(false); login(t); }} />;
  }
  return (
    <BrowserRouter>
      <AppRoutes
        deps={{ token, onUnauthorized: () => { setAuthError(true); logout(); } }}
        onLogout={logout}
      />
    </BrowserRouter>
  );
}
```

`frontend/src/pages/CockpitPage.tsx` — den globalen Header-Teil entfernen (Titel/Logout) und auf cockpit-spezifische Steuerung reduzieren:
```tsx
import { useCockpit, type UseCockpitDeps } from "../hooks/useCockpit";
import { RegimeBanner } from "../components/RegimeBanner";
import { DomainTile } from "../components/DomainTile";
import { DataHealthIndicator } from "../components/DataHealthIndicator";
import { RunControl } from "../components/RunControl";

export function CockpitPage({ deps }: { deps?: UseCockpitDeps }) {
  const { overview, phase, error, startAnalysis } = useCockpit(deps);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cockpit — Übersicht</h2>
        <div className="flex items-center gap-4">
          {overview && <DataHealthIndicator active={overview.sources_active} total={overview.sources_total} />}
          <RunControl phase={phase} onStart={startAnalysis} />
        </div>
      </div>

      {phase === "loading" && <p className="text-slate-500">Lädt …</p>}
      {phase === "error" && <p className="text-red-600">{error ?? "Backend nicht erreichbar"}</p>}
      {phase !== "loading" && phase !== "error" && phase !== "running" && !overview && (
        <p className="text-slate-500">Noch keine Analyse — starte eine über „Analyse starten".</p>
      )}

      {overview && (
        <>
          <RegimeBanner overview={overview} />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overview.domains.map((d) => (
              <DomainTile key={d.key} domain={d} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
```

> Falls ein bestehender `CockpitPage.test.tsx` den alten globalen Header (Titel „AAIA — Cockpit"/Abmelden-Button) prüft, diese Erwartungen an die neue Struktur anpassen (Titel jetzt „Cockpit — Übersicht"; Logout in der Topbar). Test entsprechend aktualisieren und grün halten.

- [ ] **Step 4: Test grün + ganze Suite + Build**

Run: `cd frontend && npx vitest run src/routes.test.tsx` → PASS.
Run: `cd frontend && npm test` → gesamte Suite grün (inkl. angepasstem CockpitPage-Test).
Run: `cd frontend && npm run build` → Build erfolgreich.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes.tsx frontend/src/routes.test.tsx frontend/src/App.tsx frontend/src/pages/CockpitPage.tsx frontend/src/pages/CockpitPage.test.tsx
git commit -m "feat(frontend): Router + Shell-Einbindung (Cockpit in der Shell, Bereiche als Platzhalter)"
```

---

## Task 12: Logbuch nachziehen

**Files:**
- Modify: `docs/open_todos.md`

- [ ] **Step 1: Eintrag ergänzen**

In `docs/open_todos.md` unter dem Frontend-Abschnitt einen Unterabschnitt „Frontend-Vollausbau — Slice 0 (Fundament + Shell, Branch `feat/frontend-vollausbau`)" ergänzen:
- **Umgesetzt:** Router + App-Shell (Sidebar/Topbar mit Suche/Inbox-Badge/Health/Theme/Logout); Tausch-Naht-Fundament (`contract/common.ts`, `data/apiDeps.ts`, `data/dataMode.ts`, `DemoBadge`, `VITE_DATA_MODE`); pure Anzeige-Logik (assets/judgment/futures/curve/anomaly) TDD-getestet; gemeinsame Bibliothek (UnderlyingWrapperBadge, LongShortPanel, XaiPanel, AnomalyReport, SourceHealth, Schwellen-Badges); ECharts-Referenz-Wrapper (ChartContainer + LineCurve); Cockpit-Übersicht in die Shell eingehängt (Live-Anbindung unverändert). Spec: `docs/superpowers/specs/2026-06-23-frontend-vollausbau-design.md`.
- **Offene Folge-Aufgaben:** Slices 1–5 (Cockpit-Drilldowns, Deep-Dive, Portfolio, Inbox, Backtester) — je eigener Plan + PR; echte Backend-Endpunkte je Bereich (Tausch-Naht vorbereitet).

- [ ] **Step 2: Commit**

```bash
git add docs/open_todos.md
git commit -m "docs(open_todos): Frontend-Vollausbau Slice 0 (Fundament + Shell) + Folge-Aufgaben"
```

---

## Self-Review (gegen die Spec)

**Spec-Abdeckung (Spec-Abschnitt → Task):**
- §2 Tausch-Naht (contract/data/DemoBadge/VITE_DATA_MODE, isDemo) → Tasks 2, 6 ✓
- §3 Shell & Navigation (Router, Sidebar, Topbar, Suche, Inbox-Badge, Health, Theme, Logout, Login-Gate, Querverlinkung Ticker→Deep-Dive) → Tasks 10, 11 ✓
- §4 Komponenten-Bibliothek (UnderlyingWrapperBadge, LongShortPanel, XaiPanel, Schwellen-Badges, AnomalyReport, SourceHealth, DemoBadge) → Tasks 6, 7 ✓
- §5 Charting ECharts (lazy) → Task 8 ✓
- §6 fachliche pure Logik (rollYield, leverage, confidenceFlags, yieldSpreadStatus, zScoreFlag, anomalySeverity, underlying/wrapper) → Tasks 3, 4, 5 ✓
- §8 Tests (pure zuerst, Komponenten-Smoke, gegen Fakes/Mocks) → durchgängig ✓
- Cockpit-Übersicht bleibt echt → Task 11 (deps/Live unverändert) ✓

**Platzhalter-Scan:** kein „TBD"/„später" in Code-Schritten; jeder Code-Schritt zeigt vollständigen Code. (Die `PlaceholderPage` ist bewusst eine echte, fertige Komponente für noch leere Bereiche — kein Code-Platzhalter.) ✓

**Typ-Konsistenz:** `Underlying`/`Wrapper`/`LongVerdict`/`ShortVerdict`/`AnomalySeverity`/`DemoMeta` (Task 2) durchgehend gleich; `confidenceFlags` (Task 4) in ThresholdBadges/LongShortPanel; `XaiContent`/`VerdictLens`/`AnomalyContent`/`FailedSource` (Task 7) konsistent; `buildLineOption`/`LineSeries` (Task 8); `AppShellProps`/`TopbarProps`/`AppRoutes` (Tasks 10/11) konsistent. ✓
