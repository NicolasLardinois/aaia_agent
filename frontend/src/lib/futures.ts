export type CurveForm = "contango" | "backwardation" | "flat";

// Anzeigename der gemeldeten Kurvenform. Normalfall: Contango => Roll-Yield<0,
// Backwardation => Roll-Yield>0. Bei Misch-/Uebergangskurven koennen Vorzeichen und
// gemeldete Form auseinanderlaufen -> die Form wird aus dem form-Argument benannt,
// nie aus dem Vorzeichen erschlossen (sonst stilles Mislabel, AGENTS.md §3).
const FORM_LABEL: Record<CurveForm, string> = {
  contango: "Contango",
  backwardation: "Backwardation",
  flat: "flach",
};

// Roll-Yield: Contango (Terminpreis > Spot) => negativ (Halten kostet, Gegenwind);
// Backwardation => positiv (Rueckenwind). Das Vorzeichen treibt den Carry-Effekt
// (Gegenwind/Rueckenwind + Farbe + Pfeil); die Kurvenform kommt aus `form`.
// Vorzeichen/Richtung benannt, nicht nur Farbe (AGENTS.md §3, Konzept §5.1).
export function rollYieldVisual(
  annualPct: number,
  form: CurveForm,
): { label: string; colorClass: string; arrow: string } {
  const formLabel = FORM_LABEL[form];
  if (annualPct < 0) return { label: `Gegenwind (${formLabel})`, colorClass: "text-bear", arrow: "▼" };
  if (annualPct > 0) return { label: `Rückenwind (${formLabel})`, colorClass: "text-bull", arrow: "▲" };
  return { label: `neutral (${formLabel})`, colorClass: "text-neutral", arrow: "→" };
}

// Hebel = Nominalwert / Margin (wahres Risiko, nicht Nominalwert). Margin<=0 => 0 (defensiv).
export function leverageFactor(notional: number, margin: number): number {
  if (margin <= 0) return 0;
  return notional / margin;
}
