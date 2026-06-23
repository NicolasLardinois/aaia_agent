// frontend/src/data/inbox.ts
// DIE TAUSCH-NAHT (Spec §2): genau EINE Lade-Funktion fuer die Inbox. Heute Demo-Fixture;
// beim Umstieg auf echt wird GENAU die auskommentierte Zeile getauscht (setzt isDemo:false).
import type { InboxView } from "../contract/inbox";
import { demoInbox } from "./demo/inbox";
import type { ApiDeps } from "./apiDeps";

export async function loadInbox(_deps?: ApiDeps): Promise<InboxView> {
  return demoInbox();
  // return fetchInbox(_deps); // <- einzige Zeile, die beim Umstieg getauscht wird
}
