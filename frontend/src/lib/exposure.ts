import type { PositionDTO } from "../contract/portfolio";

// Aktien-Klassen fuers net_beta: nur Aktien/Index haben ein Aktienmarkt-Beta
// (gespiegelt aus portfolio_monitor_agent._EQUITY_CLASSES; dort {equity,index}).
const EQUITY_UNDERLYINGS = new Set<PositionDTO["underlying"]>(["equity", "equity_index"]);

// Brutto-Exposure = Σ|Position| (long + short) in % NAV — gesamtes Markt-Engagement.
export function grossExposure(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => sum + p.sizePctNav, 0);
}

// Netto-Exposure = long − short in % NAV — die Netto-Marktrichtung.
export function netExposure(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => sum + (p.direction === "long" ? p.sizePctNav : -p.sizePctNav), 0);
}

// net_beta = Σ(signiertes Exposure × β), NUR Aktien/Index. Position mit beta=null ist
// UNAVAILABLE und wird ausgelassen (nie als 0/1 unterstellt — defensiv wie das Backend).
// Gibt es KEINE einzige verwertbare Aktien-Beta-Position, ist net_beta UNBEKANNT -> null
// (NICHT 0, denn 0 hiesse "marktneutral" — AGENTS.md §3: UNAVAILABLE ≠ 0 ≠ NEUTRAL).
export function netBeta(positions: PositionDTO[]): number | null {
  let sum = 0;
  let counted = 0; // wie viele Aktien-Positionen mit gueltigem Beta eingeflossen sind
  for (const p of positions) {
    if (!EQUITY_UNDERLYINGS.has(p.underlying) || p.beta === null) continue;
    const signed = p.direction === "long" ? p.sizePctNav : -p.sizePctNav;
    sum += signed * p.beta;
    counted += 1;
  }
  return counted === 0 ? null : sum;
}
