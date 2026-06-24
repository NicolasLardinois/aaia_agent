// Altman-Z-Klassifikation (Altman 1968 / Z''). Schwellen je Unternehmenstyp wie
// quality_agent._altman_thresholds: Manufacturing-nah -> Original-Z (safe 2.99 / distress 1.81);
// sonst Z'' (2.6 / 1.1). Financials -> nicht definiert. z=null -> UNAVAILABLE (nie 0/neutral).
// Quelle: https://de.wikipedia.org/wiki/Altman-Z-Faktor
//
// HINWEIS Sektor->Modell-Mapping ist bewusst GROB (Bucket je GICS-Sektorname) und spiegelt
// 1:1 das Backend (quality_agent). "Consumer Cyclical" enthaelt z. B. auch Nicht-Produzenten
// (Haendler) -> hier dennoch Original-Z. Akzeptiert, solange Frontend und Backend dieselben
// Sektor-Labels liefern; beim Anschluss echter Daten (Logbuch) die Label-Paritaet verifizieren.
const EXCLUDED = new Set(["Financials", "Financial Services", "Banks", "Insurance"]);
const MANUFACTURING = new Set(["Industrials", "Materials", "Manufacturing", "Consumer Cyclical"]);

export function altmanClass(
  z: number | null,
  sector: string,
): "safe" | "grey" | "distress" | "unavailable" | "not_applicable" {
  if (z === null) return "unavailable";
  if (EXCLUDED.has(sector)) return "not_applicable";
  const [safe, distress] = MANUFACTURING.has(sector) ? [2.99, 1.81] : [2.6, 1.1];
  if (z > safe) return "safe";
  if (z < distress) return "distress";
  return "grey";
}
