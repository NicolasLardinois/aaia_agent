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
export function netBeta(positions: PositionDTO[]): number {
  return positions.reduce((sum, p) => {
    if (!EQUITY_UNDERLYINGS.has(p.underlying) || p.beta === null) return sum;
    const signed = p.direction === "long" ? p.sizePctNav : -p.sizePctNav;
    return sum + signed * p.beta;
  }, 0);
}
