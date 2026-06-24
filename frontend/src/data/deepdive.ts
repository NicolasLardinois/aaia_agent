// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer den Deep-Dive. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { DeepDiveView } from "../contract/deepdive";
import { demoDeepDive } from "./demo/deepdive";
import type { ApiDeps } from "./apiDeps";

export async function loadDeepDive(ticker: string, _deps?: ApiDeps): Promise<DeepDiveView> {
  return demoDeepDive(ticker);
  // return fetchDeepDive(ticker, _deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
