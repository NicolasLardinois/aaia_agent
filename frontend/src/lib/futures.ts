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
