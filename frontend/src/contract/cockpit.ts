// Drilldown-Vertraege: beschreiben die KUENFTIGE API-Form. Demo + Echt liefern denselben
// Vertrag (Spec §2), jeder View extends DemoMeta. signal=null => UNAVAILABLE (Spec §5.4).
import type { DemoMeta } from "./common";
import type { Signal } from "../lib/contract";

// Im Drilldown auch der Health-Zaehler (US9): welche Quellen aktiv / ausgefallen.
export interface FailedSource { key: string; reason: string; }
export interface SourceHealthMeta {
  sourcesActive: number;
  sourcesTotal: number;
  failed: FailedSource[];
}

// --- Makro (US3) ---
export type InflationRegion = "USA" | "EUR" | "CH"; // EUR = Euroraum-Aggregat (ECB-HICP), NICHT Deutschland
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
  ratioPct: number;             // Marktkap/BIP x 100
  signal: Signal | null;
  zScore: number | null;        // vs. eigene 10-J-Historie (null = zu wenig Historie)
  year: number | null;          // null = Echtzeit (FRED/USA); int = letztes Weltbank-Jahr
  history: { year: number; ratioPct: number }[]; // fuer Einzelland-10-J-Drilldown
}
export interface BuffettView extends DemoMeta, SourceHealthMeta {
  countries: BuffettCountry[];
  globalMedian: number;
  analyzedIso3: string;         // hervorgehobenes Land (aus market-Param)
}

// --- Big-Mac (US7) ---
export interface BigMacRow { iso2: string; name: string; valuationPct: number; } // + = ueberbewertet vs. USD
export interface BigMacView extends DemoMeta, SourceHealthMeta {
  rows: BigMacRow[];
  publishedAt: string;          // halbjaehrlich (Jan/Jul) — sichtbar im Widget
  analyzedIso2: string;
}
