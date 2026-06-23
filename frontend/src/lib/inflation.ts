import type { Signal } from "./contract";

export type InflationRegion = "USA" | "DE" | "CH";

// Region-Schwellen (in % YoY-CPI). Begruendung (inflation_agent._signal):
// - USA + Eurozone-Laender (DE): Zielzone 1–3 %, "erhoet" 3–4 %, "hoch" >=4 %.
// - CH: strukturell niedrigere Inflation -> engeres Band: Zielzone 0.5–2 %, "erhoht" 2–3 %, "hoch" >=3 %.
// DE nutzt das USA/EU-Band (Eurozone), CH das eigene. Keine "EU"-Aggregation (frontend_notes.md).
const THRESHOLDS: Record<InflationRegion, { low: number; high: number; bearish: number }> = {
  USA: { low: 1.0, high: 3.0, bearish: 4.0 },
  DE:  { low: 1.0, high: 3.0, bearish: 4.0 },
  CH:  { low: 0.5, high: 2.0, bearish: 3.0 },
};

export interface InflationBand {
  signal: Signal | null;
  band: "deflation" | "below" | "target" | "elevated" | "high" | "unavailable";
  // Greifende Schwelle (welche Grenze gerade trennt) als Text fuers UI.
  activeThreshold: string;
}

// Lueckenlose Baender (AGENTS.md §2): jeder Wert faellt in genau eine Klasse.
export function inflationBand(cpiPct: number | null, region: InflationRegion): InflationBand {
  if (cpiPct === null) {
    return { signal: null, band: "unavailable", activeThreshold: "—" };
  }
  const t = THRESHOLDS[region];
  if (cpiPct < 0.0) {
    // Deflation drueckt nominale Gewinne / Schulden-Realwert -> BEARISH.
    return { signal: "bearish", band: "deflation", activeThreshold: `< 0 % (Deflation)` };
  }
  if (cpiPct < t.low) {
    // Unter Ziel, keine Deflation -> NEUTRAL.
    return { signal: "neutral", band: "below", activeThreshold: `< ${t.low} % (unter Ziel)` };
  }
  if (cpiPct <= t.high) {
    // Zielzone -> stuetzt -> BULLISH.
    return { signal: "bullish", band: "target", activeThreshold: `${t.low}–${t.high} % (Zielzone)` };
  }
  if (cpiPct < t.bearish) {
    // Erhoht (z. B. 3–4 % USA) -> BEARISH (vormals blinde Luecke).
    return { signal: "bearish", band: "elevated", activeThreshold: `${t.high}–${t.bearish} % (erhoht)` };
  }
  // Klar ueber Ziel -> BEARISH.
  return { signal: "bearish", band: "high", activeThreshold: `>= ${t.bearish} % (hoch)` };
}
