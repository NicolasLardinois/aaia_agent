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
