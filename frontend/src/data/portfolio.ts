// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuers Portfolio. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { PortfolioView } from "../contract/portfolio";
import { demoPortfolio } from "./demo/portfolio";
import type { ApiDeps } from "./apiDeps";

export async function loadPortfolio(_deps?: ApiDeps): Promise<PortfolioView> {
  return demoPortfolio();
  // return fetchPortfolio(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
