import { createContext, useContext, type ReactNode } from "react";
import { useCockpit, type UseCockpit, type UseCockpitDeps } from "./useCockpit";

// Hebt den Cockpit-Lauf-Zustand (WebSocket + phase/events/overview) AUS der
// CockpitPage HERAUS und stellt ihn ueber den Routen bereit. Dadurch ueberlebt
// ein laufender Lauf jede Navigation (Portfolio, Buffett, Big-Mac …) — frueher
// haengte der Zustand an der Seite und brach beim Wegnavigieren ab (Bug #5/#7).
const CockpitContext = createContext<UseCockpit | null>(null);

export function CockpitProvider({ deps, children }: { deps?: UseCockpitDeps; children: ReactNode }) {
  const cockpit = useCockpit(deps);
  return <CockpitContext.Provider value={cockpit}>{children}</CockpitContext.Provider>;
}

export function useCockpitContext(): UseCockpit {
  const ctx = useContext(CockpitContext);
  if (!ctx) throw new Error("useCockpitContext muss innerhalb von <CockpitProvider> verwendet werden");
  return ctx;
}
