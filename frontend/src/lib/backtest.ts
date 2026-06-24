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
