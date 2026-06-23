export interface SpreadStatus {
  value: number;
  inverted: boolean;
}

// Zinskurven-Spread (z. B. 10J-2J): negativ = invertiert = klassisches Rezessions-
// Fruehsignal. Richtung explizit (AGENTS.md §3).
export function yieldSpreadStatus(spread: number): SpreadStatus {
  return { value: spread, inverted: spread < 0 };
}
