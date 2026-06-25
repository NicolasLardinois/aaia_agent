import type { Signal, Domain } from "./contract";

export interface Visual {
  label: string;
  colorClass: string;
}

// Signal -> Wort + Tailwind-Farbklasse. Farben sind Design-Tokens (Instrument-Deck,
// dark-mode-fähig über .dark). null (UNAVAILABLE) ist ein eigener Zustand, NIE als
// neutrales Signal dargestellt (Spec §5.4): daher text-muted, bewusst getrennt vom
// neutral-Signal-Token (text-neutral).
export function signalToVisual(signal: Signal | null): Visual {
  switch (signal) {
    case "bullish":
      return { label: "BULLISH", colorClass: "text-bull" };
    case "bearish":
      return { label: "BEARISH", colorClass: "text-bear" };
    case "neutral":
      return { label: "NEUTRAL", colorClass: "text-neutral" };
    default:
      return { label: "nicht verfügbar", colorClass: "text-muted" };
  }
}

// Domaene gilt als ausgefallen, wenn der Status es sagt ODER kein Signal da ist.
export function isUnavailable(domain: Domain): boolean {
  return domain.status === "unavailable" || domain.signal === null;
}

export function sourcesLabel(active: number, total: number): string {
  return `${active}/${total} Quellen aktiv`;
}
