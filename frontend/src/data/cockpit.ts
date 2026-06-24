// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion je Bereich. Heute liefert sie das
// Demo-Fixture; beim Umstieg auf echt wird je Funktion GENAU EINE Zeile getauscht
// (die auskommentierte Zeile darunter). Die UI bleibt unveraendert, weil der Vertrag gleich ist.
import type { ApiDeps } from "./apiDeps";
import type {
  MacroView, CommoditiesView, SentimentView, YieldCurveView,
  SectorsView, BuffettView, BigMacView,
} from "../contract/cockpit";
import {
  demoMacro, demoCommodities, demoSentiment, demoYieldCurve,
  demoSectors, demoBuffett, demoBigMac,
} from "./demo/cockpit";

export async function loadMacro(_deps?: ApiDeps): Promise<MacroView> {
  return demoMacro();
  // return fetchMacro(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird (setzt isDemo:false)
}
export async function loadCommodities(_deps?: ApiDeps): Promise<CommoditiesView> {
  return demoCommodities();
  // return fetchCommodities(_deps);
}
export async function loadSentiment(_deps?: ApiDeps): Promise<SentimentView> {
  return demoSentiment();
  // return fetchSentiment(_deps);
}
export async function loadYieldCurve(_deps?: ApiDeps): Promise<YieldCurveView> {
  return demoYieldCurve();
  // return fetchYieldCurve(_deps);
}
export async function loadSectors(_deps?: ApiDeps): Promise<SectorsView> {
  return demoSectors();
  // return fetchSectors(_deps);
}
export async function loadBuffett(_deps?: ApiDeps): Promise<BuffettView> {
  return demoBuffett();
  // return fetchBuffett(_deps);
}
export async function loadBigMac(_deps?: ApiDeps): Promise<BigMacView> {
  return demoBigMac();
  // return fetchBigMac(_deps);
}
