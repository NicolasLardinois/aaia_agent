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
