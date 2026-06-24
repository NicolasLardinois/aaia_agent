# Frontend Slice 1 — Cockpit-Drilldowns — Implementation Plan

For agentic workers using subagent-driven-development: jeder Task ist isoliert ausführbar (eigene Dateien + Interfaces + TDD-Schritte). Reihenfolge sequentiell innerhalb eines Dispatches; Dispatch A vor B vor C (B/C hängen an der Naht + Charts aus A).

## Goal

Die **Cockpit-Übersicht** (live, PR #24/#35) bleibt echt; jede Domänen-Kachel wird **klickbar** und führt zu einem **Drilldown** (`/cockpit/<domain>`). Alle Drilldowns + die Spezial-Widgets **Buffett-Indikator** und **Big-Mac-Index** werden über die **Tausch-Naht** (Spec §2) aus **Demo-Fixtures** gespeist (`isDemo: true` → `DemoBadge`). Damit sind die User-Stories **US3–US9** sichtbar und klickbar abgedeckt (Konzept §2.1, Wireframes §4.1–4.4, §5.4). Der Umstieg auf echte Daten bleibt **pro Bereich eine Zeile**.

## Architecture

- **Hexagonal/Naht (Spec §2):** UI-Komponenten (dumm) → Bereichs-Hook `useView(loader)` → Lade-Funktion `load*()` (Naht: heute Demo, echte Zeile vorbereitet) → Vertrag (`contract/cockpit.ts`, jeder View `extends DemoMeta`). Demo **und** Echt liefern denselben Vertrag → UI bleibt beim Umstieg unverändert.
- **Pure Logik zuerst (Spec §6, AGENTS.md §4):** Schwellen-/Anzeige-Funktionen sind reine, separat getestete Funktionen (z. B. `inflationBand`, `buildBarOption`, `buildMapOption`), entkoppelt von React.
- **Wiederverwendung statt Duplikat:** bestehende Slice-0-Bausteine (`SignalBadge`, `ConfidenceBar`, `UnavailableField`, `DemoBadge`, `SourceHealth`, `LineCurve`/`buildLineOption`, `signalToVisual`/`isUnavailable`/`sourcesLabel`, `yieldSpreadStatus`, `zScoreFlag`, `formatConfidence`) werden eingebunden, nicht neu gebaut.
- **Charts:** neue Wrapper `BarChart`/`buildBarOption` und `ChoroplethMap`/`buildMapOption` nach dem Muster von `LineCurve`/`buildLineOption` (purer option-Builder, separat getestet; ECharts lazy via `ChartContainer`).

## Tech Stack

React 19 + TypeScript + Vite + Tailwind v3 + Vitest + React Testing Library; `react-router-dom` v7; `echarts` + `echarts-for-react` (lazy). Keine neuen Runtime-Dependencies außer der Welt-GeoJSON-Datei (`frontend/public/world.geo.json`, Download-Step).

## Global Constraints

> Verbatim bindend (aus Auftrag / Spec / AGENTS.md):

- **Tausch-Naht exemplarisch:** generischer Konsum-Hook `data/useView.ts` (`useView(loader) => { data, loading, error }`); pro Bereich **genau eine** `load*()`-Funktion mit Demo-Implementierung unter `data/demo/`; Vertrag in `contract/cockpit.ts`, jeder View-Typ `extends DemoMeta` (`isDemo`). Echte Variante als **auskommentierte** Zeile danebenstellen. „Eine Zeile tauschen" muss vorgeführt sein.
- **Neue Chart-Wrapper mit purem, separat getestetem option-Builder** (wie `buildLineOption`): `BarChart`/`buildBarOption` (horizontale Balken, Farbe nach Vorzeichen) und `ChoroplethMap`/`buildMapOption`. Welt-GeoJSON als `frontend/public/world.geo.json` (Download-Step) + im Component **lazy registrieren**, **mit grazilem Fallback** („Karte nicht verfügbar"), falls die GeoJSON fehlt. Scheitert der Download im Umsetzungs-Schritt, **als Concern flaggen, nicht faken**.
- **TDD verpflichtend**, pure Logik/Builder zuerst. Grenzfälle explizit (genau auf Schwelle, knapp darüber/darunter, `null`, negativ).
- **UI-Texte/Kommentare Deutsch.**
- **UNAVAILABLE ≠ 0 ≠ NEUTRAL** (eigener Zustand, gestreift-grau, aus Aggregaten ausgenommen, via `SourceHealth` gezählt).
- **Keine magischen Zahlen ohne Begründungskommentar** (fachliche Begründung jeder Schwelle, Spec §6 / AGENTS.md §3).
- **Keine „EU"-Aggregation** — einzelne Länder (DE/CH/USA), unterschiedliche Inflations-Schwellen je Region.
- **Demo-Daten müssen nur plausibel sein, nicht exakt** — Annahmen im Plan vermerkt.

---

## File-Structure (Datei → Verantwortung)

| Datei | Verantwortung |
|---|---|
| `frontend/src/contract/cockpit.ts` | **Neu.** Alle Drilldown-Verträge: `MacroView`, `CommoditiesView`, `SentimentView`, `YieldCurveView`, `SectorsView`, `BuffettView`, `BigMacView` + Hilfstypen; alle `extends DemoMeta`; `FailedSource[]` je View. |
| `frontend/src/data/useView.ts` | **Neu.** Generischer Konsum-Hook `useView(loader) => { data, loading, error }`. |
| `frontend/src/data/cockpit.ts` | **Neu.** Die Naht: je eine `load*()`-Funktion (`loadMacro`, `loadCommodities`, `loadSentiment`, `loadYieldCurve`, `loadSectors`, `loadBuffett`, `loadBigMac`). Heute Demo, echte Zeile auskommentiert. |
| `frontend/src/data/demo/cockpit.ts` | **Neu.** Alle Demo-Fixtures (fachlich plausibel, `isDemo:true`, inkl. bewusster UNAVAILABLE-Zustände). |
| `frontend/src/lib/inflation.ts` | **Neu.** Pure `inflationBand(cpi, region)` → greifender Schwellenwert + Signal (spiegelt `inflation_agent._signal`). |
| `frontend/src/lib/buffett.ts` | **Neu.** Pure Tabellen-Logik: `sortRows`, `filterRows` (Z-Ausreißer/BEARISH), `vsMedianLabel`. |
| `frontend/src/components/charts/BarChart.tsx` | **Neu.** `buildBarOption(bars)` (horizontale Balken, Farbe nach Vorzeichen) + `BarChart`-Wrapper. |
| `frontend/src/components/charts/ChoroplethMap.tsx` | **Neu.** `buildMapOption(points)` + `ChoroplethMap`-Wrapper mit lazy GeoJSON-Registrierung + Fallback. |
| `frontend/public/world.geo.json` | **Neu (Download-Step).** Welt-GeoJSON für die Choropleth-Karte. |
| `frontend/src/pages/cockpit/MacroDrilldown.tsx` | **Neu.** Makro-Drilldown (US3): Inflation je Region + greifende Schwelle. |
| `frontend/src/pages/cockpit/CommoditiesDrilldown.tsx` | **Neu.** Rohstoff-Signal-Liste. |
| `frontend/src/pages/cockpit/SentimentDrilldown.tsx` | **Neu.** VIX/Fear&Greed-Sub-Signale. |
| `frontend/src/pages/cockpit/YieldCurveDrilldown.tsx` | **Neu.** Kurve (`LineCurve`) + 3 Spreads + Inversion (US4). |
| `frontend/src/pages/cockpit/SectorsDrilldown.tsx` | **Neu.** Sektor-Rotation je Regime + UNAVAILABLE-Pfad (US8). |
| `frontend/src/pages/cockpit/BuffettWidget.tsx` | **Neu.** Tabelle (default) + Karten-Tab + Einzelland-10-J-Drilldown + Einschränkungen + Asset-Filter (US5/US6). |
| `frontend/src/pages/cockpit/BigMacWidget.tsx` | **Neu.** Balken (`BarChart`) + Publikationsdatum (US7). |
| `frontend/src/pages/cockpit/DrilldownShell.tsx` | **Neu.** Gemeinsames Drilldown-Gerüst: Titel, „← zurück zur Übersicht", `DemoBadge`, `SourceHealth`, loading/error. |
| `frontend/src/components/DomainTile.tsx` | **Modify.** Kachel klickbar (Link auf `/cockpit/<domain>`); inkl. Makro-Kachel. |
| `frontend/src/pages/CockpitPage.tsx` | **Modify.** Macht die Übersichts-Kacheln klickbar (inkl. Makro) + verlinkt Buffett/Big-Mac. |
| `frontend/src/routes.tsx` | **Modify.** Neue Routen `/cockpit/:domain`, `/cockpit/buffett`, `/cockpit/big-mac`. |

---

## Dispatch A — Naht, pure Helfer & Chart-Wrapper

### Task A1 — Vertrag `contract/cockpit.ts`

**Files**
- Create: `frontend/src/contract/cockpit.ts`
- Test: `frontend/src/contract/cockpit.test.ts` (Typ-Smoke: Demo-Fixture erfüllt Vertrag — kombiniert mit A4)

**Interfaces** (Produces — exakte Typen):

```ts
// frontend/src/contract/cockpit.ts
// Drilldown-Verträge: beschreiben die KÜNFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag (Spec §2), jeder View extends DemoMeta. signal=null => UNAVAILABLE (Spec §5.4).
import type { DemoMeta } from "./common";
import type { Signal } from "../lib/contract";

// Im Drilldown auch der Health-Zähler (US9): welche Quellen aktiv / ausgefallen.
export interface FailedSource { key: string; reason: string; }
export interface SourceHealthMeta {
  sourcesActive: number;
  sourcesTotal: number;
  failed: FailedSource[];
}

// --- Makro (US3) ---
export type InflationRegion = "USA" | "DE" | "CH"; // einzelne Länder, KEINE "EU"-Aggregation
export interface InflationRow {
  region: InflationRegion;
  cpiPct: number | null;        // YoY-CPI in Prozent (3.0 = 3 %); null => UNAVAILABLE
  signal: Signal | null;
  dataDate: string;             // Stand der Daten (Stale-vs-fehlend, Spec §5.4)
}
export interface MacroView extends DemoMeta, SourceHealthMeta {
  inflation: InflationRow[];
}

// --- Rohstoffe ---
export interface CommodityRow { name: string; ticker: string; signal: Signal | null; note: string; }
export interface CommoditiesView extends DemoMeta, SourceHealthMeta {
  commodities: CommodityRow[];
}

// --- Sentiment ---
export interface SentimentRow { name: string; value: number | null; signal: Signal | null; note: string; }
export interface SentimentView extends DemoMeta, SourceHealthMeta {
  subSignals: SentimentRow[];
}

// --- Zinskurve (US4) ---
export interface CurvePoint { tenor: "3M" | "2J" | "10J" | "30J"; yieldPct: number; }
export type SpreadPair = "10J-2J" | "10J-3M" | "30J-10J"; // Richtung explizit (AGENTS.md §3)
export interface SpreadRow { pair: SpreadPair; value: number; } // value = vorderes minus hinteres Tenor, in %-Punkten
export interface YieldCurveView extends DemoMeta, SourceHealthMeta {
  points: CurvePoint[];
  spreads: SpreadRow[];
}

// --- Sektoren (US8) ---
export interface SectorRow { sector: string; rotation: "favored" | "neutral" | "avoid"; signal: Signal | null; }
export interface SectorsView extends DemoMeta, SourceHealthMeta {
  regime: string;
  sectors: SectorRow[];
}

// --- Buffett (US5/US6) ---
export interface BuffettCountry {
  iso3: string;                 // z. B. "USA", "CHE", "DEU"
  name: string;
  ratioPct: number;             // Marktkap/BIP × 100
  signal: Signal | null;
  zScore: number | null;        // vs. eigene 10-J-Historie (null = zu wenig Historie)
  year: number | null;          // null = Echtzeit (FRED/USA); int = letztes Weltbank-Jahr
  history: { year: number; ratioPct: number }[]; // für Einzelland-10-J-Drilldown
}
export interface BuffettView extends DemoMeta, SourceHealthMeta {
  countries: BuffettCountry[];
  globalMedian: number;
  analyzedIso3: string;         // hervorgehobenes Land (aus market-Param)
}

// --- Big-Mac (US7) ---
export interface BigMacRow { iso2: string; name: string; valuationPct: number; } // + = überbewertet vs. USD
export interface BigMacView extends DemoMeta, SourceHealthMeta {
  rows: BigMacRow[];
  publishedAt: string;          // halbjährlich (Jan/Jul) — sichtbar im Widget
  analyzedIso2: string;
}
```

**Steps**
- [ ] Vertrag schreiben (oben). Kein eigener Laufzeit-Test nötig (reine Typen) — die Typ-Konsistenz wird in A4 durch das Demo-Fixture geprüft (Fixture muss Vertrag erfüllen → `tsc` schlägt sonst fehl).
- [ ] `npm run build` (tsc) muss grün sein.
- [ ] Commit: `feat(frontend): Vertrag contract/cockpit.ts für Slice-1-Drilldowns`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A2 — Generischer Hook `data/useView.ts`

**Files**
- Create: `frontend/src/data/useView.ts`
- Test: `frontend/src/data/useView.test.tsx`

**Interfaces**
- Consumes: `loader: () => Promise<T>`
- Produces: `useView<T>(loader: () => Promise<T>): { data: T | null; loading: boolean; error: string | null }`

**Vollständiger Code:**

```ts
// frontend/src/data/useView.ts
import { useEffect, useState } from "react";

// Generischer Konsum-Hook für die Tausch-Naht (Spec §2): nimmt eine Lade-Funktion
// (Demo ODER echt — identischer Vertrag) und liefert data/loading/error. Die UI weiß
// nicht, ob die Daten Demo oder echt sind — das steht im Vertrag (isDemo).
export function useView<T>(loader: () => Promise<T>): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    loader()
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError("Daten nicht ladbar"); setLoading(false); } });
    return () => { cancelled = true; };
    // loader-Identität steuert den Refetch; Aufrufer muss loader stabil halten (useCallback/Modul-Fn).
  }, [loader]);

  return { data, loading, error };
}
```

**Kern-Test-Assertions:**
```tsx
// useView.test.tsx
// 1) Erfolg: loading wird false, data gesetzt.
//    const loader = () => Promise.resolve({ ok: 1 });
//    renderHook(() => useView(loader)) -> waitFor: result.current.data toEqual {ok:1}, loading false, error null
// 2) Fehler: loader rejected -> error "Daten nicht ladbar", data null, loading false.
// 3) Unmount vor Resolve: kein setState-Warning (cancelled greift).
```

**Steps**
- [ ] Test schreiben (failing) → rot laufen (`npm test -- useView`).
- [ ] `useView` implementieren → grün.
- [ ] Commit: `feat(frontend): generischer useView-Hook für die Tausch-Naht`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A3 — Pure Inflations-Logik `lib/inflation.ts`

**Files**
- Create: `frontend/src/lib/inflation.ts`
- Test: `frontend/src/lib/inflation.test.ts`

**Interfaces**
- Consumes: `cpiPct: number | null`, `region: InflationRegion`
- Produces:
```ts
export interface InflationBand {
  signal: Signal | null;        // null bei cpi === null (UNAVAILABLE)
  band: "deflation" | "below" | "target" | "elevated" | "high" | "unavailable";
  // Greifende Schwelle (welche Grenze gerade trennt) als Text fürs UI.
  activeThreshold: string;
}
```

**Vollständiger Code** (spiegelt `agents/market_cockpit/macro/inflation_agent.py::_signal`, vereinfachte CPI-only-Variante fürs UI — Trend/Core/PPI/Realzins-Modifikatoren sind Backend-Sache):

```ts
// frontend/src/lib/inflation.ts
import type { Signal } from "./contract";

export type InflationRegion = "USA" | "DE" | "CH";

// Region-Schwellen (in % YoY-CPI). Begründung (inflation_agent._signal):
// - USA + Eurozone-Länder (DE): Zielzone 1–3 %, "erhöht" 3–4 %, "hoch" >=4 %.
// - CH: strukturell niedrigere Inflation -> engeres Band: Zielzone 0.5–2 %, "erhöht" 2–3 %, "hoch" >=3 %.
// DE nutzt das USA/EU-Band (Eurozone), CH das eigene. Keine "EU"-Aggregation (frontend_notes.md).
const THRESHOLDS: Record<InflationRegion, { low: number; high: number; bearish: number }> = {
  USA: { low: 1.0, high: 3.0, bearish: 4.0 },
  DE:  { low: 1.0, high: 3.0, bearish: 4.0 },
  CH:  { low: 0.5, high: 2.0, bearish: 3.0 },
};

export interface InflationBand {
  signal: Signal | null;
  band: "deflation" | "below" | "target" | "elevated" | "high" | "unavailable";
  activeThreshold: string;
}

// Lückenlose Bänder (AGENTS.md §2): jeder Wert fällt in genau eine Klasse.
export function inflationBand(cpiPct: number | null, region: InflationRegion): InflationBand {
  if (cpiPct === null) {
    return { signal: null, band: "unavailable", activeThreshold: "—" };
  }
  const t = THRESHOLDS[region];
  if (cpiPct < 0.0) {
    // Deflation drückt nominale Gewinne / Schulden-Realwert -> BEARISH.
    return { signal: "bearish", band: "deflation", activeThreshold: `< 0 % (Deflation)` };
  }
  if (cpiPct < t.low) {
    // Unter Ziel, keine Deflation -> NEUTRAL.
    return { signal: "neutral", band: "below", activeThreshold: `< ${t.low} % (unter Ziel)` };
  }
  if (cpiPct <= t.high) {
    // Zielzone -> stützt -> BULLISH.
    return { signal: "bullish", band: "target", activeThreshold: `${t.low}–${t.high} % (Zielzone)` };
  }
  if (cpiPct < t.bearish) {
    // Erhöht (z. B. 3–4 % USA) -> BEARISH (vormals blinde Lücke).
    return { signal: "bearish", band: "elevated", activeThreshold: `${t.high}–${t.bearish} % (erhöht)` };
  }
  // Klar über Ziel -> BEARISH.
  return { signal: "bearish", band: "high", activeThreshold: `>= ${t.bearish} % (hoch)` };
}
```

**Kern-Test-Assertions (Grenzfälle explizit):**
```ts
// inflation.test.ts
// USA: -0.1 -> deflation/bearish; 0.0 -> below/neutral (>=0, <1); 0.9 -> below; 1.0 -> target/bullish (Grenze inklusiv);
//      3.0 -> target/bullish (Grenze inklusiv); 3.1 -> elevated/bearish; 4.0 -> high/bearish; 5.0 -> high/bearish.
// CH:  0.5 -> target (Grenze inklusiv); 2.0 -> target; 2.1 -> elevated; 3.0 -> high.
// null -> unavailable/signal null, activeThreshold "—".
// activeThreshold ist je Band der greifende Wert (string-Match auf erwarteten Text).
```

**Steps**
- [ ] Test (failing) → rot.
- [ ] `inflationBand` implementieren → grün.
- [ ] Commit: `feat(frontend): pure Inflations-Schwellen-Logik je Region (USA/DE/CH)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A4 — Naht + Demo-Fixtures (`data/cockpit.ts` + `data/demo/cockpit.ts`)

**Files**
- Create: `frontend/src/data/cockpit.ts`
- Create: `frontend/src/data/demo/cockpit.ts`
- Test: `frontend/src/data/cockpit.test.ts`

**Interfaces**
- Consumes: `ApiDeps` (aus `data/apiDeps.ts`)
- Produces (jede `load*` gibt den jeweiligen Vertrag, `isDemo:true`):
```ts
export function loadMacro(_deps?: ApiDeps): Promise<MacroView>;
export function loadCommodities(_deps?: ApiDeps): Promise<CommoditiesView>;
export function loadSentiment(_deps?: ApiDeps): Promise<SentimentView>;
export function loadYieldCurve(_deps?: ApiDeps): Promise<YieldCurveView>;
export function loadSectors(_deps?: ApiDeps): Promise<SectorsView>;
export function loadBuffett(_deps?: ApiDeps): Promise<BuffettView>;
export function loadBigMac(_deps?: ApiDeps): Promise<BigMacView>;
```

**Vollständiger Code — Naht (`data/cockpit.ts`):**

```ts
// frontend/src/data/cockpit.ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion je Bereich. Heute liefert sie das
// Demo-Fixture; beim Umstieg auf echt wird je Funktion GENAU EINE Zeile getauscht
// (die auskommentierte Zeile darunter). Die UI bleibt unverändert, weil der Vertrag gleich ist.
import type { ApiDeps } from "./apiDeps";
import type {
  MacroView, CommoditiesView, SentimentView, YieldCurveView,
  SectorsView, BuffettView, BigMacView,
} from "../contract/cockpit";
import {
  demoMacro, demoCommodities, demoSentiment, demoYieldCurve,
  demoSectors, demoBuffett, demoBigMac,
} from "./demo/cockpit";

export async function loadMacro(_deps?: ApiDeps): Promise<MacroView> {
  return demoMacro();
  // return fetchMacro(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird (setzt isDemo:false)
}
export async function loadCommodities(_deps?: ApiDeps): Promise<CommoditiesView> {
  return demoCommodities();
  // return fetchCommodities(_deps);
}
export async function loadSentiment(_deps?: ApiDeps): Promise<SentimentView> {
  return demoSentiment();
  // return fetchSentiment(_deps);
}
export async function loadYieldCurve(_deps?: ApiDeps): Promise<YieldCurveView> {
  return demoYieldCurve();
  // return fetchYieldCurve(_deps);
}
export async function loadSectors(_deps?: ApiDeps): Promise<SectorsView> {
  return demoSectors();
  // return fetchSectors(_deps);
}
export async function loadBuffett(_deps?: ApiDeps): Promise<BuffettView> {
  return demoBuffett();
  // return fetchBuffett(_deps);
}
export async function loadBigMac(_deps?: ApiDeps): Promise<BigMacView> {
  return demoBigMac();
  // return fetchBigMac(_deps);
}
```

**Vollständiger Code — Demo-Fixtures (`data/demo/cockpit.ts`):**

> **Demo-Annahmen (plausibel, nicht exakt):** Werte stimmig zum AUFSCHWUNG-Regime der Cockpit-Übersicht. Inflations-Werte so gewählt, dass jede Region in ein anderes Band fällt (Demo zeigt alle Pfade). Sektoren enthält **bewusst** einen UNAVAILABLE-Eintrag (Spec §1/§5.4). Buffett-Werte angelehnt an reale Größenordnungen (USA ~190 %, CH ~210 %, DE ~55 %; Global-Median ~90 %).

```ts
// frontend/src/data/demo/cockpit.ts
// Fachlich plausible Beispielwerte (Spec §1: Demo-Daten, nicht exakt). isDemo:true -> DemoBadge.
import type {
  MacroView, CommoditiesView, SentimentView, YieldCurveView,
  SectorsView, BuffettView, BigMacView,
} from "../../contract/cockpit";

export function demoMacro(): MacroView {
  return {
    isDemo: true,
    sourcesActive: 3, sourcesTotal: 3, failed: [],
    inflation: [
      // USA 3.2 % -> "erhöht" (3–4 %) -> BEARISH; EU/DE 2.4 % -> Zielzone -> BULLISH;
      // CH 1.1 % -> über CH-Ziel-Untergrenze, in CH-Zielzone (0.5–2) -> BULLISH.
      { region: "USA", cpiPct: 3.2, signal: "bearish", dataDate: "2026-05" },
      { region: "DE",  cpiPct: 2.4, signal: "bullish", dataDate: "2026-05" },
      { region: "CH",  cpiPct: 1.1, signal: "bullish", dataDate: "2026-05" },
    ],
  };
}

export function demoCommodities(): CommoditiesView {
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    commodities: [
      { name: "Rohöl (WTI)", ticker: "CL=F", signal: "bullish", note: "Angebotsdisziplin OPEC+, Nachfrage robust" },
      { name: "Kupfer",      ticker: "HG=F", signal: "bearish", note: "Konjunktursorgen China dämpfen" },
      { name: "Erdgas",      ticker: "NG=F", signal: "neutral", note: "saisonal ausgeglichen" },
    ],
  };
}

export function demoSentiment(): SentimentView {
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    subSignals: [
      // VIX ~18 = moderat; Fear&Greed 62 = leichte Gier -> mild bearish (überhitzt).
      { name: "VIX", value: 18.2, signal: "neutral", note: "moderate Volatilität" },
      { name: "Fear & Greed", value: 62, signal: "bearish", note: "leichte Gier (überhitzt)" },
    ],
  };
}

export function demoYieldCurve(): YieldCurveView {
  return {
    isDemo: true,
    sourcesActive: 1, sourcesTotal: 1, failed: [],
    // Aufwärts geneigte Kurve (nicht invertiert) -> kein Rezessions-Frühsignal -> BULLISH.
    points: [
      { tenor: "3M",  yieldPct: 3.9 },
      { tenor: "2J",  yieldPct: 4.1 },
      { tenor: "10J", yieldPct: 4.5 },
      { tenor: "30J", yieldPct: 4.7 },
    ],
    // value = vorderes minus hinteres Tenor (in %-Punkten); positiv = nicht invertiert.
    spreads: [
      { pair: "10J-2J",  value: +0.4 },
      { pair: "10J-3M",  value: +0.6 },
      { pair: "30J-10J", value: +0.2 },
    ],
  };
}

export function demoSectors(): SectorsView {
  return {
    isDemo: true,
    // Bewusst eine Quelle ausgefallen -> UNAVAILABLE-Pfad demonstrieren (Spec §1/§5.4).
    sourcesActive: 2, sourcesTotal: 3,
    failed: [{ key: "Sektor-Momentum (Stub)", reason: "Datenquelle noch nicht angebunden" }],
    regime: "AUFSCHWUNG",
    sectors: [
      // Frühzyklisch begünstigt: zyklischer Konsum, Industrie, Technologie.
      { sector: "Technologie",        rotation: "favored", signal: "bullish" },
      { sector: "Zyklischer Konsum",  rotation: "favored", signal: "bullish" },
      { sector: "Industrie",          rotation: "favored", signal: "bullish" },
      { sector: "Versorger",          rotation: "avoid",   signal: "bearish" },
      { sector: "Basiskonsum",        rotation: "neutral", signal: "neutral" },
      // Ausgefallene Sub-Quelle -> signal null -> UNAVAILABLE (nicht 0, nicht neutral).
      { sector: "Energie",            rotation: "neutral", signal: null },
    ],
  };
}

export function demoBuffett(): BuffettView {
  // Plausible Größenordnungen; history je Land für den 10-J-Drilldown.
  const usaHist = [150, 160, 175, 200, 210, 185, 195, 188, 192, 198].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  const cheHist = [180, 190, 205, 230, 240, 215, 222, 210, 218, 211].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  const deuHist = [48, 50, 55, 62, 64, 54, 58, 53, 56, 55].map((r, i) => ({ year: 2017 + i, ratioPct: r }));
  return {
    isDemo: true,
    sourcesActive: 2, sourcesTotal: 2, failed: [],
    globalMedian: 92,       // globaler Median über alle Länder (Referenz)
    analyzedIso3: "USA",    // hervorgehobenes Land
    countries: [
      // ratio>135 -> BEARISH (absoluter Fallback); USA z=+2.1 (>2 = Anomalie/auffällig).
      { iso3: "USA", name: "USA",     ratioPct: 198, signal: "bearish", zScore: +2.1, year: null, history: usaHist },
      { iso3: "CHE", name: "Schweiz", ratioPct: 211, signal: "bearish", zScore: +0.6, year: 2024, history: cheHist },
      { iso3: "DEU", name: "Deutschland", ratioPct: 55, signal: "bullish", zScore: -0.9, year: 2024, history: deuHist },
      { iso3: "JPN", name: "Japan",   ratioPct: 145, signal: "bearish", zScore: +1.6, year: 2024, history: [] },
      { iso3: "GBR", name: "UK",      ratioPct: 100, signal: "neutral", zScore: -0.2, year: 2024, history: [] },
    ],
  };
}

export function demoBigMac(): BigMacView {
  return {
    isDemo: true,
    sourcesActive: 1, sourcesTotal: 1, failed: [],
    publishedAt: "2026-01", // halbjährlich (Jan/Jul) — sichtbar im Widget
    analyzedIso2: "US",
    rows: [
      // + = überbewertet vs. USD, − = unterbewertet. CHF traditionell stark überbewertet.
      { iso2: "CH", name: "Schweiz", valuationPct: +38.0 },
      { iso2: "NO", name: "Norwegen", valuationPct: +21.0 },
      { iso2: "US", name: "USA",     valuationPct: 0.0 },
      { iso2: "JP", name: "Japan",   valuationPct: -41.0 },
      { iso2: "IN", name: "Indien",  valuationPct: -52.0 },
    ],
  };
}
```

**Kern-Test-Assertions:**
```ts
// cockpit.test.ts
// Für JEDE load*-Funktion:
//  - liefert den Vertrag mit isDemo === true (Naht-Test, Spec §8).
//  - SourceHealthMeta konsistent: failed.length === sourcesTotal - sourcesActive.
// loadSectors: enthält genau einen sector mit signal === null (UNAVAILABLE-Pfad).
// loadMacro: 3 Regionen USA/DE/CH; KEIN "EU"-Eintrag.
// loadYieldCurve: 3 Spreads mit den Paaren "10J-2J","10J-3M","30J-10J".
// loadBuffett: analyzedIso3 in countries vorhanden; globalMedian > 0.
```

**Steps**
- [ ] Test (failing) → rot.
- [ ] Demo-Fixtures + Naht implementieren → grün. `npm run build` (tsc) muss grün sein (Typ-Konsistenz Vertrag↔Fixture).
- [ ] Commit: `feat(frontend): Tausch-Naht loadCockpit* + Demo-Fixtures (Slice 1)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A5 — `BarChart`/`buildBarOption`

**Files**
- Create: `frontend/src/components/charts/BarChart.tsx`
- Test: `frontend/src/components/charts/BarChart.test.tsx`

**Interfaces**
```ts
export interface Bar { label: string; value: number; highlight?: boolean }
export function buildBarOption(bars: Bar[]): any; // horizontale Balken, Farbe nach Vorzeichen
export function BarChart({ bars, height }: { bars: Bar[]; height?: number }): JSX.Element;
```

**Vollständiger Code:**

```tsx
// frontend/src/components/charts/BarChart.tsx
import { ChartContainer } from "./ChartContainer";

export interface Bar { label: string; value: number; highlight?: boolean }

// Pure: horizontale Balken, Farbe NACH VORZEICHEN (+ grün / − rot / 0 grau-blau);
// hervorgehobener Balken (analysiertes Land) bekommt einen Rahmen. Separat testbar.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildBarOption(bars: Bar[]): any {
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: { type: "value" },
    // yAxis category bei horizontalen Balken; Reihenfolge umkehren, damit erster Eintrag oben steht.
    yAxis: { type: "category", data: bars.map((b) => b.label).reverse() },
    series: [{
      type: "bar",
      data: bars.map((b) => ({
        value: b.value,
        itemStyle: {
          // Signal-Farbkonvention (Konzept §4): + grün, − rot, 0 grau-blau.
          color: b.value > 0 ? "#16a34a" : b.value < 0 ? "#dc2626" : "#64748b",
          borderColor: b.highlight ? "#0f172a" : "transparent",
          borderWidth: b.highlight ? 2 : 0,
        },
      })).reverse(),
    }],
  };
}

export function BarChart({ bars, height }: { bars: Bar[]; height?: number }) {
  return <ChartContainer option={buildBarOption(bars)} height={height} />;
}
```

**Kern-Test-Assertions:**
```tsx
// BarChart.test.tsx  (vi.mock("echarts-for-react", () => ({ default: () => null })))
// buildBarOption([{label:"CH",value:38},{label:"JP",value:-41,highlight:true}]):
//  - yAxis.type === "category"; xAxis.type === "value" (horizontal).
//  - data[0] entspricht dem LETZTEN bar (reverse): JP, color rot (#dc2626), borderWidth 2 (highlight).
//  - positiver Wert -> grün (#16a34a); 0 -> grau-blau (#64748b).
```

**Steps**
- [ ] Test (failing) → rot.
- [ ] `buildBarOption`/`BarChart` implementieren → grün.
- [ ] Commit: `feat(frontend): BarChart-Wrapper + buildBarOption (Farbe nach Vorzeichen)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A6 — `ChoroplethMap`/`buildMapOption` + Welt-GeoJSON

**Files**
- Create: `frontend/src/components/charts/ChoroplethMap.tsx`
- Create: `frontend/public/world.geo.json` (Download-Step)
- Test: `frontend/src/components/charts/ChoroplethMap.test.tsx`

**Interfaces**
```ts
export interface MapPoint { iso3: string; name: string; value: number; signal: "bullish" | "bearish" | "neutral" | null }
export function buildMapOption(points: MapPoint[], mapName: string): any; // visualMap rot↔grün, Länder eingefärbt
export function ChoroplethMap({ points, height }: { points: MapPoint[]; height?: number }): JSX.Element;
```

**Vollständiger Code:**

```tsx
// frontend/src/components/charts/ChoroplethMap.tsx
import { lazy, Suspense, useEffect, useState } from "react";

const ReactECharts = lazy(() => import("echarts-for-react"));

export interface MapPoint { iso3: string; name: string; value: number; signal: "bullish" | "bearish" | "neutral" | null }

const MAP_NAME = "world";

// Pure: baut die Choropleth-option. visualMap kontinuierlich grün (niedrig/günstig) ->
// rot (hoch/überbewertet), passend zur Signal-Farbkonvention. Separat testbar.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildMapOption(points: MapPoint[], mapName: string = MAP_NAME): any {
  const values = points.map((p) => p.value);
  return {
    tooltip: { trigger: "item", formatter: (p: { name: string; value: number }) => `${p.name}: ${p.value ?? "—"}` },
    visualMap: {
      min: Math.min(...values, 0),
      max: Math.max(...values, 100),
      calculable: true,
      // grün = niedrig (günstig), rot = hoch (überbewertet) — Buffett-Logik.
      inRange: { color: ["#16a34a", "#fde047", "#dc2626"] },
    },
    series: [{
      type: "map",
      map: mapName,
      nameProperty: "name",
      data: points.map((p) => ({ name: p.name, value: p.value })),
    }],
  };
}

// Lazy-Registrierung der Welt-GeoJSON. Fehlt sie (Download im Umsetzungs-Schritt
// gescheitert), zeigt das Component einen GRAZILEN FALLBACK statt zu crashen.
export function ChoroplethMap({ points, height = 360 }: { points: MapPoint[]; height?: number }) {
  const [status, setStatus] = useState<"loading" | "ready" | "missing">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const echarts = await import("echarts");
        const res = await fetch("/world.geo.json");
        if (!res.ok) throw new Error("geojson missing");
        const geo = await res.json();
        echarts.registerMap(MAP_NAME, geo);
        if (!cancelled) setStatus("ready");
      } catch {
        if (!cancelled) setStatus("missing"); // grazile Degradierung
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (status === "missing") {
    return <div className="rounded border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">Karte nicht verfügbar — bitte Tabelle nutzen.</div>;
  }
  if (status === "loading") {
    return <div className="text-sm text-slate-500">Karte lädt …</div>;
  }
  return (
    <Suspense fallback={<div className="text-sm text-slate-500">Karte lädt …</div>}>
      <ReactECharts option={buildMapOption(points)} style={{ height }} notMerge lazyUpdate />
    </Suspense>
  );
}
```

**Kern-Test-Assertions:**
```tsx
// ChoroplethMap.test.tsx  (vi.mock("echarts-for-react", () => ({ default: () => null })))
// buildMapOption([{iso3:"USA",name:"USA",value:198,signal:"bearish"},...]):
//  - series[0].type === "map"; series[0].map === "world".
//  - series[0].data hat einen Eintrag je point mit {name, value}.
//  - visualMap.inRange.color beginnt grün, endet rot (Buffett-Farbskala).
// (Das Component selbst rendert in jsdom den missing-Fallback, wenn fetch("/world.geo.json")
//  fehlschlägt — separater Smoke-Test optional.)
```

**Welt-GeoJSON Download-Step (robust):**
- [ ] Welt-GeoJSON nach `frontend/public/world.geo.json` beziehen (z. B. öffentliche `world.geo.json`-Datei mit `name`-Property je Land). Bevorzugt ein im Web frei verfügbares ECharts-kompatibles Welt-GeoJSON. Quelle + Lizenz im Commit notieren.
- [ ] **Wenn der Download scheitert:** NICHT faken. Datei weglassen, das Component zeigt automatisch den „Karte nicht verfügbar"-Fallback (Tabelle bleibt voll funktionsfähig). Den fehlenden Download als **Concern** im PR/Logbuch flaggen (Folge-Task: GeoJSON nachziehen).

**Steps**
- [ ] Test (failing) → rot.
- [ ] `buildMapOption`/`ChoroplethMap` implementieren → grün.
- [ ] GeoJSON-Download versuchen (s. o.); Ergebnis dokumentieren.
- [ ] Commit: `feat(frontend): ChoroplethMap-Wrapper + buildMapOption (+ Welt-GeoJSON / Fallback)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task A7 — Pure Buffett-Tabellen-Logik `lib/buffett.ts`

**Files**
- Create: `frontend/src/lib/buffett.ts`
- Test: `frontend/src/lib/buffett.test.ts`

**Interfaces**
```ts
import type { BuffettCountry } from "../contract/cockpit";
export type SortKey = "ratioPct" | "zScore" | "name";
export function sortRows(rows: BuffettCountry[], key: SortKey, dir: "asc" | "desc"): BuffettCountry[];
export interface BuffettFilters { onlyZOutlier: boolean; onlyBearish: boolean }
export function filterRows(rows: BuffettCountry[], f: BuffettFilters): BuffettCountry[];
export function vsMedianLabel(ratioPct: number, median: number): { label: string; ratio: number };
```

**Vollständiger Code:**

```ts
// frontend/src/lib/buffett.ts
import type { BuffettCountry } from "../contract/cockpit";
import { zScoreFlag } from "./anomaly";

export type SortKey = "ratioPct" | "zScore" | "name";

// Stabile Sortierung; null-zScore ans Ende (defensiv, Spec §6 / Datenrealität).
export function sortRows(rows: BuffettCountry[], key: SortKey, dir: "asc" | "desc"): BuffettCountry[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (key === "name") return sign * a.name.localeCompare(b.name);
    const av = key === "zScore" ? a.zScore : a.ratioPct;
    const bv = key === "zScore" ? b.zScore : b.ratioPct;
    if (av === null) return 1;   // null immer ans Ende
    if (bv === null) return -1;
    return sign * (av - bv);
  });
}

export interface BuffettFilters { onlyZOutlier: boolean; onlyBearish: boolean }

// Filter (Konzept §4.3): nur Z-Ausreißer (|Z|>=1.5 -> zScoreFlag !== "none") und/oder nur BEARISH.
export function filterRows(rows: BuffettCountry[], f: BuffettFilters): BuffettCountry[] {
  return rows.filter((r) => {
    if (f.onlyZOutlier && (r.zScore === null || zScoreFlag(r.zScore) === "none")) return false;
    if (f.onlyBearish && r.signal !== "bearish") return false;
    return true;
  });
}

// vs. Median: Verhältnis + Wort. Median<=0 defensiv -> ratio 0.
export function vsMedianLabel(ratioPct: number, median: number): { label: string; ratio: number } {
  if (median <= 0) return { label: "—", ratio: 0 };
  const ratio = ratioPct / median;
  const label = ratio >= 1.5 ? "deutlich >" : ratio > 1.0 ? ">" : ratio < 0.67 ? "deutlich <" : "<";
  return { label, ratio };
}
```

**Kern-Test-Assertions (Grenzfälle):**
```ts
// buffett.test.ts
// sortRows ratioPct desc: höchste ratio zuerst; zScore mit null -> null-Land ganz hinten (beide Richtungen).
// filterRows onlyZOutlier: behält |Z|>=1.5 (z=+1.6 ja, z=+1.5 ja Grenze, z=+0.6 nein, z=null nein).
// filterRows onlyBearish: nur signal==="bearish".
// beide Filter zugleich: Schnittmenge.
// vsMedianLabel(198,92) -> ratio>1.0, label ">" oder "deutlich >" (198/92≈2.15 -> "deutlich >");
//   vsMedianLabel(55,92) -> "deutlich <" (0.6<0.67); vsMedianLabel(92,92) -> "<" (ratio 1.0 Grenze, nicht >1.0).
```

**Steps**
- [ ] Test (failing) → rot.
- [ ] Implementieren → grün.
- [ ] Commit: `feat(frontend): pure Buffett-Tabellen-Logik (Sortierung/Filter/vs-Median)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Dispatch B — Drilldown-Seiten + klickbare Kacheln + Routing

### Task B1 — Gemeinsames Drilldown-Gerüst `DrilldownShell.tsx`

**Files**
- Create: `frontend/src/pages/cockpit/DrilldownShell.tsx`
- Test: `frontend/src/pages/cockpit/DrilldownShell.test.tsx`

**Interfaces**
```ts
import type { DemoMeta } from "../../contract/common";
import type { SourceHealthMeta } from "../../contract/cockpit";
export function DrilldownShell({ title, view, loading, error, children }: {
  title: string;
  view: (DemoMeta & SourceHealthMeta) | null;
  loading: boolean;
  error: string | null;
  children: React.ReactNode;
}): JSX.Element;
```

**Strukturvorgabe (Implementierer baut JSX nach Slice-0-Mustern):**
- Kopfzeile: `title` + **„← zurück zur Übersicht"** als `<Link to="/cockpit">` + `<DemoBadge isDemo={view?.isDemo ?? false} />`.
- Health-Zeile: `<SourceHealth active={view.sourcesActive} total={view.sourcesTotal} failed={view.failed} />` (US9).
- loading → „Lädt …"; error → roter Text (wie `CockpitPage`); sonst `children`.

**Kern-Test-Assertions:**
```tsx
// DrilldownShell.test.tsx (MemoryRouter)
// - rendert title + Link "zurück" mit href "/cockpit".
// - view.isDemo true -> "Demo-Daten" sichtbar; false -> nicht.
// - failed-Liste -> SourceHealth zeigt x/y + ⚠.
// - loading true -> "Lädt …"; error gesetzt -> Fehlertext, children NICHT gerendert.
```

**Steps**
- [ ] Test (failing) → rot.
- [ ] Implementieren → grün.
- [ ] Commit: `feat(frontend): DrilldownShell (Zurück-Link, DemoBadge, SourceHealth)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B2 — Makro-Drilldown (US3)

**Files**
- Create: `frontend/src/pages/cockpit/MacroDrilldown.tsx`
- Test: `frontend/src/pages/cockpit/MacroDrilldown.test.tsx`

**Interfaces**
- Consumes: `useView(loadMacro)`, `inflationBand`, `SignalBadge`, `UnavailableField`, `DrilldownShell`.
- Produces: `MacroDrilldown(): JSX.Element`.

**Strukturvorgabe:** Tabelle/Liste je Region (USA/DE/CH) mit: Region, CPI %, `SignalBadge` (oder `UnavailableField` bei `signal===null`), **greifender Schwellenwert** aus `inflationBand(row.cpiPct, row.region).activeThreshold`, `dataDate`. Kurzer Begründungstext je Band. Klar: keine „EU"-Zeile.

**Kern-Test-Assertions:**
```tsx
// MacroDrilldown.test.tsx (loader = () => Promise.resolve(demoMacro()))
// - zeigt USA, DE, CH (KEINE "EU"-Zeile).
// - USA-Zeile zeigt den greifenden Schwellentext (z. B. "3–4 % (erhöht)") + BEARISH-Badge.
// - DE-Zeile zeigt "1–3 % (Zielzone)" + BULLISH; CH passende CH-Schwelle.
// - Demo-Badge sichtbar.
```

**Steps**
- [ ] Test (failing) → rot. → implementieren → grün.
- [ ] Commit: `feat(frontend): Makro-Drilldown — Inflation je Region + greifende Schwelle (US3)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B3 — Rohstoffe-Drilldown

**Files**
- Create: `frontend/src/pages/cockpit/CommoditiesDrilldown.tsx`
- Test: `frontend/src/pages/cockpit/CommoditiesDrilldown.test.tsx`

**Strukturvorgabe:** `useView(loadCommodities)`; Liste der Rohstoffe mit Name, `SignalBadge`, Note. Innerhalb `DrilldownShell`.

**Kern-Test-Assertions:**
```tsx
// - zeigt "Rohöl (WTI)" mit BULLISH und "Kupfer" mit BEARISH.
// - Demo-Badge sichtbar.
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Rohstoffe-Drilldown (Signal-Liste)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B4 — Sentiment-Drilldown

**Files**
- Create: `frontend/src/pages/cockpit/SentimentDrilldown.tsx`
- Test: `frontend/src/pages/cockpit/SentimentDrilldown.test.tsx`

**Strukturvorgabe:** `useView(loadSentiment)`; Sub-Signale (VIX, Fear & Greed) mit Wert + `SignalBadge` + Note.

**Kern-Test-Assertions:**
```tsx
// - zeigt "VIX" (18.2) und "Fear & Greed" (62) mit Signal-Badges.
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Sentiment-Drilldown (VIX/Fear&Greed-Sub-Signale)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B5 — Zinskurve-Drilldown (US4)

**Files**
- Create: `frontend/src/pages/cockpit/YieldCurveDrilldown.tsx`
- Test: `frontend/src/pages/cockpit/YieldCurveDrilldown.test.tsx`

**Interfaces**
- Consumes: `useView(loadYieldCurve)`, `LineCurve`/`buildLineOption` (Laufzeiten 3M/2J/10J/30J), `yieldSpreadStatus` (aus `lib/curve.ts`).

**Strukturvorgabe (Wireframe §4.2):**
- `LineCurve` mit einer Serie „Rendite", `points = view.points.map(p => ({ x: p.tenor, y: p.yieldPct }))`.
- Die drei Spreads `10J-2J`, `10J-3M`, `30J-10J` je mit Wert + Richtung; `yieldSpreadStatus(value).inverted` steuert das Invertierungs-Flag.
- Gesamt-Status: invertiert (mind. ein Spread negativ) → „invertiert → Rezessions-Frühsignal"; sonst „nicht invertiert → kein Frühsignal". Vorzeichen/Richtung der Paare im Text benannt (`10J−2J` usw.).

**Kern-Test-Assertions:**
```tsx
// (vi.mock echarts-for-react)
// - zeigt die 3 Spread-Paare mit Werten (+0.4, +0.6, +0.2) und Vorzeichen.
// - Status "nicht invertiert" (alle positiv).
// - separater Fall: ein negativer Spread -> "invertiert" + Flag.
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Zinskurve-Drilldown — Kurve + 3 Spreads + Inversion (US4)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B6 — Sektoren-Drilldown (US8, UNAVAILABLE-Pfad)

**Files**
- Create: `frontend/src/pages/cockpit/SectorsDrilldown.tsx`
- Test: `frontend/src/pages/cockpit/SectorsDrilldown.test.tsx`

**Strukturvorgabe (US8 + Spec §5.4):**
- `useView(loadSectors)`; Überschrift nennt das `regime`.
- Liste je Sektor: Name, Rotation (favored/neutral/avoid als Wort), `SignalBadge` — **außer** wenn `signal===null`, dann `UnavailableField` (gestreift-grau, nicht neutral).
- `DrilldownShell` zeigt `SourceHealth` mit `failed` → 2/3 aktiv + ⚠ (US9).

**Kern-Test-Assertions:**
```tsx
// - zeigt regime "AUFSCHWUNG".
// - "Technologie" favored/BULLISH; "Versorger" avoid/BEARISH.
// - "Energie"-Zeile zeigt UnavailableField ("nicht verfügbar"), NICHT NEUTRAL/0.
// - SourceHealth zeigt "2/3 Quellen aktiv" + ⚠.
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Sektoren-Drilldown — Rotation je Regime + UNAVAILABLE-Pfad (US8/US9)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task B7 — Klickbare Kacheln + Routing

**Files**
- Modify: `frontend/src/components/DomainTile.tsx`
- Modify: `frontend/src/pages/CockpitPage.tsx`
- Modify: `frontend/src/routes.tsx`
- Test: `frontend/src/components/DomainTile.test.tsx` (neu), `frontend/src/routes.test.tsx` (erweitern)

**Strukturvorgabe:**
- `DomainTile`: bekommt optionales `to`-Ziel und wird zum `<Link to={`/cockpit/${key}`}>` (key→Route-Slug: `commodities`/`sentiment`/`yield_curve`→`yield-curve`/`sectors`). Bestehende UNAVAILABLE-Anzeige bleibt.
- `CockpitPage`: die Makro-Kachel (heute über `RegimeBanner`/`macro_status` repräsentiert) zusätzlich als klickbare Kachel zu `/cockpit/macro`; Domänen-Kacheln verlinken auf ihren Drilldown. Buffett/Big-Mac als zwei verlinkte Buttons/Tabs (`/cockpit/buffett`, `/cockpit/big-mac`).
- `routes.tsx`: neue Kind-Routen unter der Shell:
  - `/cockpit/macro` → `MacroDrilldown`
  - `/cockpit/commodities` → `CommoditiesDrilldown`
  - `/cockpit/sentiment` → `SentimentDrilldown`
  - `/cockpit/yield-curve` → `YieldCurveDrilldown`
  - `/cockpit/sectors` → `SectorsDrilldown`
  - `/cockpit/buffett` → `BuffettWidget` (Task C1)
  - `/cockpit/big-mac` → `BigMacWidget` (Task C2)
  - `/cockpit` bleibt die Übersicht (`CockpitPage`).

**Kern-Test-Assertions:**
```tsx
// routes.test.tsx: Navigation zu "/cockpit/yield-curve" rendert den Zinskurve-Drilldown
//   (Titel sichtbar). "/cockpit/macro" rendert Makro-Drilldown.
// DomainTile.test.tsx: Kachel "Rohstoffe" ist ein Link mit href "/cockpit/commodities".
//   Klick navigiert (MemoryRouter + Routes-Smoke).
```

**Steps**
- [ ] Tests (failing) → rot → grün. `npm run build` grün.
- [ ] Commit: `feat(frontend): Cockpit-Kacheln klickbar + Drilldown-Routen (/cockpit/<domain>)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Dispatch C — Buffett-Widget + Big-Mac-Widget + Routen

### Task C1 — Buffett-Widget (US5/US6)

**Files**
- Create: `frontend/src/pages/cockpit/BuffettWidget.tsx`
- Test: `frontend/src/pages/cockpit/BuffettWidget.test.tsx`

**Interfaces**
- Consumes: `useView(loadBuffett)`, `sortRows`/`filterRows`/`vsMedianLabel` (`lib/buffett.ts`), `zScoreFlag` (`lib/anomaly.ts`), `SignalBadge`, `ChoroplethMap` (Karten-Tab), `LineCurve` (Einzelland-10-J-Drilldown), `DrilldownShell`.
- Produces: `BuffettWidget(): JSX.Element`.

**Strukturvorgabe (Wireframe §4.3, frontend_notes Buffett):**
- **Tab-Umschalter** `[Tabelle ▣][Karte ◻]`, **Tabelle als Default**.
- **Tabelle** (sortierbar nach ratioPct/zScore/name via `sortRows`): Spalten Land · Ratio% · Signal (`SignalBadge`) · Z-Score (mit ⚠ wenn `zScoreFlag(z)!=="none"`, also |Z|≥1.5) · Jahr (`year===null` → „live"; sonst Jahreszahl — Stale-Label, Spec §5.4) · vs. Median (`vsMedianLabel`).
- **Analysiertes Land hervorgehoben** (`row.iso3 === view.analyzedIso3` → Zeilen-Highlight).
- **Global-Median** als Referenz sichtbar (Kopf der Tabelle).
- **Filter** „nur Z-Ausreißer (|Z|≥1.5)" + „nur BEARISH" via `filterRows`.
- **Einschränkungen** (Pflicht, frontend_notes): Globalisierung · Zinskontext · kein Timing · Aktienrückkäufe — sichtbar (aufklappbar erlaubt, aber im DOM vorhanden).
- **Asset-Filter-Hinweis:** „nur für Aktien/ETF/Index relevant".
- **Karten-Tab:** `ChoroplethMap` mit `points` aus countries (value=ratioPct, signal). Bei fehlender GeoJSON greift der Fallback automatisch.
- **Einzelland-10-J-Drilldown:** Klick auf eine Zeile öffnet eine `LineCurve` der `history` (x=Jahr, y=ratioPct) des Landes (Inline-Panel/Aufklappung).

**Kern-Test-Assertions:**
```tsx
// (vi.mock echarts-for-react; loader = demoBuffett)
// - Default-Ansicht = Tabelle: USA-, Schweiz-, Deutschland-Zeilen sichtbar.
// - USA-Zeile hervorgehoben (analyzedIso3) + Z=+2.1 trägt ⚠ (|Z|>=1.5).
// - "year===null" USA zeigt "live"; CHE zeigt "2024".
// - Global-Median 92 sichtbar.
// - Filter "nur BEARISH" -> Deutschland (bullish) verschwindet; "nur Z-Ausreißer" -> nur USA & JPN (|Z|>=1.5) bleiben.
// - Einschränkungs-Texte (Globalisierung/Zinskontext/Timing/Aktienrückkäufe) im DOM.
// - Tab "Karte" wechselbar (Karten-Container/Fallback erscheint).
// - Klick auf USA-Zeile zeigt das 10-J-Drilldown-Panel (LineCurve-Container).
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Buffett-Widget — Tabelle/Karte/10-J-Drilldown + Filter + Einschränkungen (US5/US6)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task C2 — Big-Mac-Widget (US7)

**Files**
- Create: `frontend/src/pages/cockpit/BigMacWidget.tsx`
- Test: `frontend/src/pages/cockpit/BigMacWidget.test.tsx`

**Interfaces**
- Consumes: `useView(loadBigMac)`, `BarChart`/`buildBarOption` (Task A5), `DrilldownShell`.

**Strukturvorgabe (Wireframe §4.4, frontend_notes Big-Mac):**
- **Balken** (`BarChart`) der Über-/Unterbewertung vs. USD: `bars = rows.map(r => ({ label: r.name, value: r.valuationPct, highlight: r.iso2 === view.analyzedIso2 }))`. Farbe nach Vorzeichen (über buildBarOption).
- **Analysiertes Land hervorgehoben** (highlight).
- **Publikationsdatum** sichtbar (`publishedAt`, halbjährlich Jan/Jul).
- Einschränkungen optional (einklappbar).

**Kern-Test-Assertions:**
```tsx
// (vi.mock echarts-for-react)
// - Publikationsdatum "2026-01" sichtbar.
// - buildBarOption bekommt einen highlight-Bar für analyzedIso2 (US) -> über die Daten prüfbar
//   (oder: Komponente rendert Balken-Container + Datum + Demo-Badge).
// - Demo-Badge sichtbar.
```

**Steps**
- [ ] Test (failing) → rot → grün.
- [ ] Commit: `feat(frontend): Big-Mac-Widget — Balken + Publikationsdatum (US7)`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

### Task C3 — Buffett/Big-Mac in Cockpit-Navigation einhängen

**Files**
- Modify: `frontend/src/pages/CockpitPage.tsx` (Tabs/Links zu `/cockpit/buffett`, `/cockpit/big-mac`)
- Modify: `frontend/src/routes.tsx` (Routen auf die echten Widgets statt Platzhalter, falls in B7 noch Platzhalter)
- Test: `frontend/src/routes.test.tsx` (erweitern)

**Kern-Test-Assertions:**
```tsx
// routes.test.tsx: "/cockpit/buffett" rendert Buffett-Widget (Tabelle), "/cockpit/big-mac" rendert Big-Mac-Widget.
// CockpitPage zeigt Links/Tabs "Buffett-Indikator" und "Big-Mac-Index".
```

**Steps**
- [ ] Test (failing) → rot → grün. `npm run build` grün, voller `npm test` grün.
- [ ] Commit: `feat(frontend): Buffett-/Big-Mac-Routen + Cockpit-Verlinkung`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Logbuch-Task (am Ende)

### Task L1 — Logbuch + offene Folge-Aufgaben

**Files**
- Modify: `docs/open_todos.md`

**Steps**
- [ ] Slice-1-Eintrag ergänzen: was gebaut (Cockpit-Drilldowns + Buffett/Big-Mac über Demo-Naht, US3–US9), wie gelöst (Tausch-Naht `useView`/`load*`/`demo/`, neue Chart-Wrapper).
- [ ] **Folge-Aufgaben** mit Lösungsansatz eintragen:
  - Echte Endpunkte je Bereich anbinden (je die eine vorbereitete `fetch*`-Zeile in `data/cockpit.ts` aktivieren, `isDemo:false`).
  - **Welt-GeoJSON:** falls Download im Umsetzungs-Schritt scheiterte → GeoJSON nachziehen (`frontend/public/world.geo.json`); bis dahin greift der Karten-Fallback.
  - Inflations-UI bildet nur die CPI-Bänder ab; Core/PPI/Trend/Realzins-Modifikatoren (Backend `inflation_agent`) später spiegeln, falls gewünscht.
- [ ] **Kein** direkter Master-Commit von Code — nur dieser Logbuch-Vermerk ist (gemäß AGENTS.md §5) master-erlaubt; der restliche Slice läuft über den PR.
- [ ] Commit: `docs(open_todos): Frontend-Slice 1 (Cockpit-Drilldowns) protokolliert + Folge-Tasks`
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

## Self-Review

### Spec-/US-Abdeckung (US3–US9 → Task)

| US | Inhalt | Task(s) |
|---|---|---|
| **US3** | Inflation je Region (USA/DE/CH) + greifende Schwelle | A3 (`inflationBand`) + B2 (Makro-Drilldown) |
| **US4** | Zinskurve (3M/2J/10J/30J) + 3 Spreads + Inversion | A4 (Fixture) + B5 (Zinskurve-Drilldown, `LineCurve`+`yieldSpreadStatus`) |
| **US5** | Buffett ~Länder, sortier-/filterbar, Land hervorgehoben, Z-Score, Datenjahr, vs. Median, Karte, 10-J-Drilldown | A6 (`ChoroplethMap`) + A7 (`buffett.ts`) + C1 (Buffett-Widget) |
| **US6** | Buffett-Einschränkungen am Widget (Pflicht) | C1 (Einschränkungen-Block) |
| **US7** | Big-Mac Über-/Unterbewertung vs. USD + Publikationsdatum | A5 (`BarChart`) + C2 (Big-Mac-Widget) |
| **US8** | Sektor-Rotation passend zum Regime | A4 (Fixture) + B6 (Sektoren-Drilldown) |
| **US9** | Ausgefallene Quellen je Drilldown sichtbar | B1 (`DrilldownShell`+`SourceHealth`) + B6 (UNAVAILABLE-Pfad sichtbar) — durchgängig in allen Drilldowns |

Zusätzlich: klickbare Kacheln + Routing (B7), Buffett/Big-Mac-Routen (C3) bilden die Navigations-Vorgabe ab.

### Platzhalter-Scan
- Kein `TODO`/`FIXME`/leerer Funktionskörper in produktivem Code. Die **einzige** absichtliche Auslassung: die auskommentierte `fetch*`-Zeile pro Naht (Spec §2 — das ist Vorgabe, kein Platzhalter-Bug) und eine **evtl. fehlende** `world.geo.json` (graziler Fallback + Concern-Flag, kein Fake).
- Demo-Fixtures sind konkret befüllt (keine leeren Arrays außer bewusst leerer `history`/`failed`).

### Typ-Konsistenz
- Jeder View `extends DemoMeta` (`isDemo`) **und** `SourceHealthMeta` → `DemoBadge`/`SourceHealth` greifen einheitlich.
- `Signal | null` durchgängig (UNAVAILABLE = `null`), nie `0`/`"neutral"` als Ersatz.
- `InflationRegion` (USA/DE/CH) deckungsgleich zwischen `contract/cockpit.ts` und `lib/inflation.ts` — keine „EU".
- Fixtures erfüllen die Verträge → `tsc -b` (`npm run build`) ist der Typ-Gate vor jedem „grün".

### Dispatch-Gruppierung (explizit)
- **A (Naht + Charts + pure Helfer):** A1 Vertrag · A2 `useView` · A3 `inflationBand` · A4 Naht+Fixtures · A5 `BarChart` · A6 `ChoroplethMap`+GeoJSON · A7 `buffett.ts`.
- **B (Drilldown-Seiten + Kacheln + Routing):** B1 `DrilldownShell` · B2 Makro · B3 Rohstoffe · B4 Sentiment · B5 Zinskurve · B6 Sektoren · B7 klickbare Kacheln + Routen.
- **C (Buffett + Big-Mac + Routen):** C1 Buffett-Widget · C2 Big-Mac-Widget · C3 Routen+Cockpit-Verlinkung.
- **Abschluss:** L1 Logbuch.

> Reihenfolge: A vor B vor C (B/C konsumieren Naht + Charts aus A); L1 zuletzt.
