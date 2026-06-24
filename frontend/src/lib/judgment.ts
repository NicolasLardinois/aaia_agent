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
