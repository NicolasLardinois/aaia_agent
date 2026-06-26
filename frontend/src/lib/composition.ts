// Portfolio-Zusammensetzung (Mangel #12: Portfolio-Monitor ausbauen). Reine Aggregationen
// AUS den Positionen — keine handgesetzten/erfundenen Zahlen, garantiert konsistent zur Tabelle.
// Ergaenzt die Klumpen-Warnungen (die NUR Limit-Ueberschreitungen zeigen) um die VOLLE Verteilung.
import type { PositionDTO } from "../contract/portfolio";
import { detectConflict } from "./conflict";

export type AllocationDimension = "underlying" | "sector" | "geography";

export interface AllocationSlice {
  name: string;       // Gruppen-Schluessel: underlying-Key bzw. Sektor-/Geographie-Name
  grossPct: number;   // Σ|Position| dieser Gruppe in NAV-Punkten
  sharePct: number;   // Anteil am gesamten Brutto-Exposure in % (0..100)
}

function dimValue(p: PositionDTO, dim: AllocationDimension): string {
  if (dim === "sector") return p.sector;
  if (dim === "geography") return p.geography;
  return p.underlying;
}

// Allokation je Dimension. Nenner ist das BRUTTO-Exposure (Σ|Position|, long UND short positiv),
// weil die Allokation das gesamte Markt-Engagement aufschluesselt — nicht die Netto-Richtung.
// Absteigend nach Punkten (groesste Konzentration zuerst); Gleichstand alphabetisch (deterministisch).
export function allocationBy(positions: PositionDTO[], dim: AllocationDimension): AllocationSlice[] {
  const gross = positions.reduce((s, p) => s + p.sizePctNav, 0);
  const byName = new Map<string, number>();
  for (const p of positions) {
    const key = dimValue(p, dim);
    byName.set(key, (byName.get(key) ?? 0) + p.sizePctNav);
  }
  const slices = [...byName.entries()].map(([name, grossPct]) => ({
    name,
    grossPct: Number(grossPct.toFixed(2)),
    sharePct: gross === 0 ? 0 : Number(((grossPct / gross) * 100).toFixed(1)),
  }));
  slices.sort((a, b) => b.grossPct - a.grossPct || a.name.localeCompare(b.name));
  return slices;
}

export interface LongShortSplit {
  grossLongPct: number;   // Σ long in NAV-Punkten
  grossShortPct: number;  // Σ short in NAV-Punkten
  netPct: number;         // long − short (Netto-Marktrichtung)
  longCount: number;
  shortCount: number;
}

// Long/Short-Aufteilung: trennt das Brutto-Engagement nach Richtung. Macht die Total-Return-
// Idee (Rendite in beide Marktrichtungen) sichtbar — wie viel Kapital auf Long vs. Short wettet.
export function longShortSplit(positions: PositionDTO[]): LongShortSplit {
  let gl = 0, gs = 0, lc = 0, sc = 0;
  for (const p of positions) {
    if (p.direction === "long") { gl += p.sizePctNav; lc += 1; }
    else { gs += p.sizePctNav; sc += 1; }
  }
  return {
    grossLongPct: Number(gl.toFixed(2)),
    grossShortPct: Number(gs.toFixed(2)),
    netPct: Number((gl - gs).toFixed(2)),
    longCount: lc,
    shortCount: sc,
  };
}

export interface JudgmentAlignment { aligned: number; conflict: number; total: number; }

// Urteils-Einklang: bei wie vielen Positionen STUETZT AAIA die gehaltene Richtung (kein Konflikt)
// vs. laeuft dagegen (Konflikt). Nutzt dieselbe detectConflict-Quelle wie Tabelle + Inbox.
export function judgmentAlignment(positions: PositionDTO[]): JudgmentAlignment {
  let conflict = 0;
  for (const p of positions) if (detectConflict(p.direction, p.judgment)) conflict += 1;
  return { aligned: positions.length - conflict, conflict, total: positions.length };
}
