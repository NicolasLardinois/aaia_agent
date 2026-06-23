import type { BuffettCountry } from "../contract/cockpit";
import { zScoreFlag } from "./anomaly";

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
