import type { Signal, Domain } from "./contract";

export interface Visual {
  label: string;
  colorClass: string;
}

// Signal -> Wort + Tailwind-Farbklasse. null (UNAVAILABLE) ist ein eigener
// Zustand, NIE als neutrales Signal dargestellt (Spec §5.4).
export function signalToVisual(signal: Signal | null): Visual {
  switch (signal) {
    case "bullish":
      return { label: "BULLISH", colorClass: "text-green-600" };
    case "bearish":
      return { label: "BEARISH", colorClass: "text-red-600" };
    case "neutral":
      return { label: "NEUTRAL", colorClass: "text-slate-500" };
    default:
      return { label: "nicht verfügbar", colorClass: "text-slate-400" };
  }
}

// Domaene gilt als ausgefallen, wenn der Status es sagt ODER kein Signal da ist.
export function isUnavailable(domain: Domain): boolean {
  return domain.status === "unavailable" || domain.signal === null;
}

export function sourcesLabel(active: number, total: number): string {
  return `${active}/${total} Quellen aktiv`;
}
