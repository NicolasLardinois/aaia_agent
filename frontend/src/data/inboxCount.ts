// frontend/src/data/inboxCount.ts
// Schlanker Lader fuer die Topbar-Badge-Zahl (US28): laedt die Inbox ueber die Naht und
// zaehlt die OFFENEN Konflikte (openCount). Getrennt vom Cockpit-Datenpfad -> stoert die
// useCockpit-Live-Anbindung nicht. Reset bei Reload akzeptabel (kein Backend, Demo).
import { loadInbox } from "./inbox";
import { openCount } from "../lib/inbox";
import type { ApiDeps } from "./apiDeps";

export async function loadInboxCount(deps?: ApiDeps): Promise<number> {
  const view = await loadInbox(deps);
  return openCount(view.conflicts);
}
