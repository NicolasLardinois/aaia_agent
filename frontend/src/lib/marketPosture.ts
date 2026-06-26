import type { Domain } from "./contract";

// ---- Markt-Puls: transparente Synthese der Domaenen-Signale ----
//
// Fachlicher Hintergrund: Das Cockpit zeigt vier Domaenen (Rohstoffe, Sentiment,
// Zinskurve, Sektoren) jeweils mit einem Signal bullish/bearish/neutral. Der
// "Markt-Puls" verdichtet diese bereits sichtbaren Einzelsignale zu einer
// Tendenz auf einen Blick — er ist KEINE neue Bewertung, sondern eine
// nachvollziehbare Mehrheits-Auszaehlung. Deshalb bewusst simpel gehalten:
//   bullish > bearish  -> risk-on  (Mehrheit konstruktiv)
//   bearish > bullish  -> risk-off (Mehrheit vorsichtig)
//   Gleichstand        -> mixed
//   keine Daten        -> unknown
// Neutrale Signale ziehen die Tendenz bewusst NICHT in eine Richtung; sie
// zaehlen nur in die Verteilung. Nicht verfuegbare Domaenen (status=unavailable
// oder signal=null) gelten als "ohne Daten" und nicht als neutral — sonst wuerde
// eine ausgefallene Quelle faelschlich als Gleichgewicht interpretiert.

export type Tone = "risk-on" | "risk-off" | "mixed" | "unknown";

export interface Posture {
  bullish: number;
  bearish: number;
  neutral: number;
  unavailable: number;
  /** Summe der Domaenen mit echtem Signal (bullish+bearish+neutral). */
  available: number;
  tone: Tone;
}

export function marketPosture(domains: Domain[]): Posture {
  let bullish = 0;
  let bearish = 0;
  let neutral = 0;
  let unavailable = 0;

  for (const d of domains) {
    // Defensiv: fehlendes Signal ODER unavailable -> ohne Daten.
    if (d.status === "unavailable" || d.signal === null) {
      unavailable += 1;
      continue;
    }
    if (d.signal === "bullish") bullish += 1;
    else if (d.signal === "bearish") bearish += 1;
    else neutral += 1;
  }

  const available = bullish + bearish + neutral;
  let tone: Tone;
  if (available === 0) tone = "unknown";
  else if (bullish > bearish) tone = "risk-on";
  else if (bearish > bullish) tone = "risk-off";
  else tone = "mixed";

  return { bullish, bearish, neutral, unavailable, available, tone };
}

// Deutscher Klartext je Tendenz (fuer Nutzer ohne Finanz-Vorwissen).
const TONE_LABEL: Record<Tone, string> = {
  "risk-on": "Risikofreudige Tendenz",
  "risk-off": "Defensive Tendenz",
  mixed: "Gemischtes Bild",
  unknown: "Keine Daten",
};

export function postureLabel(tone: Tone): string {
  return TONE_LABEL[tone];
}
