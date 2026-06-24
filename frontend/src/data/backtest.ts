// frontend/src/data/backtest.ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer den Backtester. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { BacktestView } from "../contract/backtest";
import { demoBacktest } from "./demo/backtest";
import type { ApiDeps } from "./apiDeps";

export async function loadBacktest(_deps?: ApiDeps): Promise<BacktestView> {
  return demoBacktest();
  // return fetchBacktest(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
