import type { BuffettCountry } from "../contract/cockpit";
import type { MapPoint } from "../components/charts/ChoroplethMap";
import { zScoreFlag } from "./anomaly";

// GeoJSON (frontend/public/world.geo.json) traegt nur ENGLISCHE Laendernamen, kein ISO-Property.
// Die Demo-Daten (und zukuenftige API-Daten) verwenden deutsche Namen + iso3.
// Damit buildMapOption() die Laender per nameProperty:"name" findet, muessen die MapPoints
// den exakten englischen GeoJSON-Namen tragen — sonst bleibt die Karte grau (kein Match).
const ISO3_TO_MAP_NAME: Record<string, string> = {
  USA: "United States",
  CHE: "Switzerland",
  DEU: "Germany",
  JPN: "Japan",
  GBR: "United Kingdom",
};

// Wandelt BuffettCountry-Eintraege in MapPoints fuer ChoroplethMap um.
// Neue Laender: ISO3_TO_MAP_NAME ergaenzen (Wert = exakter name in world.geo.json).
export function toMapPoints(countries: BuffettCountry[]): MapPoint[] {
  return countries.map((c) => ({
    iso3: c.iso3,
    name: ISO3_TO_MAP_NAME[c.iso3] ?? c.name, // Fallback: behalte deutschen Namen
    value: c.ratioPct,
    signal: c.signal,
  }));
}

export type SortKey = "ratioPct" | "zScore" | "name";

// Stabile Sortierung; null-zScore ans Ende (defensiv, Spec §6 / Datenrealitaet).
export function sortRows(rows: BuffettCountry[], key: SortKey, dir: "asc" | "desc"): BuffettCountry[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (key === "name") return sign * a.name.localeCompare(b.name);
    const av = key === "zScore" ? a.zScore : a.ratioPct;
    const bv = key === "zScore" ? b.zScore : b.ratioPct;
    if (av === null) return 1;   // null immer ans Ende
    if (bv === null) return -1;
    return sign * (av - bv);
  });
}

export interface BuffettFilters { onlyZOutlier: boolean; onlyBearish: boolean }

// Filter (Konzept §4.3): nur Z-Ausreisser (|Z|>=1.5 -> zScoreFlag !== "none") und/oder nur BEARISH.
export function filterRows(rows: BuffettCountry[], f: BuffettFilters): BuffettCountry[] {
  return rows.filter((r) => {
    if (f.onlyZOutlier && (r.zScore === null || zScoreFlag(r.zScore) === "none")) return false;
    if (f.onlyBearish && r.signal !== "bearish") return false;
    return true;
  });
}

// vs. Median: Verhaeltnis + Wort. Median<=0 defensiv -> ratio 0.
// Lückenlose Bänder: [0.95, 1.05] -> "≈ am Median" (praktisch am Median)
export function vsMedianLabel(ratioPct: number, median: number): { label: string; ratio: number } {
  if (median <= 0) return { label: "—", ratio: 0 };
  const ratio = ratioPct / median;
  let label: string;
  if (ratio >= 1.5) label = "deutlich >";
  else if (ratio > 1.05) label = ">";
  else if (ratio >= 0.95) label = "≈ am Median"; // ratio in [0.95, 1.05] -> praktisch am Median
  else if (ratio < 0.67) label = "deutlich <";
  else label = "<";
  return { label, ratio };
}
