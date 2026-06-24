import { Navigate, Route, Routes } from "react-router-dom";
import { useState, useEffect } from "react";
import { AppShell } from "./shell/AppShell";
import { CockpitPage } from "./pages/CockpitPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { MacroDrilldown } from "./pages/cockpit/MacroDrilldown";
import { CommoditiesDrilldown } from "./pages/cockpit/CommoditiesDrilldown";
import { SentimentDrilldown } from "./pages/cockpit/SentimentDrilldown";
import { YieldCurveDrilldown } from "./pages/cockpit/YieldCurveDrilldown";
import { SectorsDrilldown } from "./pages/cockpit/SectorsDrilldown";
import { BuffettWidget } from "./pages/cockpit/BuffettWidget";
import { BigMacWidget } from "./pages/cockpit/BigMacWidget";
import { DeepDivePage } from "./pages/DeepDivePage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { InboxPage } from "./pages/InboxPage";
import { loadInboxCount } from "./data/inboxCount";
import type { UseCockpitDeps } from "./hooks/useCockpit";

// Routen unter der Shell. Inbox-Anzahl wird einmalig ueber loadInboxCount geladen (Slice 4, US28).
// Drilldown-Routen (B7): /cockpit/<domain> -> jeweilige Drilldown-Seite.
// Buffett + Big-Mac (Dispatch C, C3): echte Widgets eingehaengt.
export function AppRoutes({ deps, onLogout }: { deps?: UseCockpitDeps; onLogout?: () => void }) {
  // Offene Konflikt-Anzahl fuer den Topbar-Badge (US28). Getrennter Datenpfad — stoert useCockpit nicht.
  // Fehler werden still geschluckt (bleibt 0, kein Crash). Reset bei Reload akzeptabel (Demo).
  const [inboxCount, setInboxCount] = useState<number>(0);
  useEffect(() => {
    loadInboxCount(deps && deps.token ? { token: deps.token } : undefined)
      .then(setInboxCount)
      .catch(() => {/* Fehler still -> Badge bleibt 0 */});
  // Einmaliger Ladeaufruf beim Mount. deps wird nicht erneut beobachtet (Demo-Vereinfachung).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route element={<AppShell inboxCount={inboxCount} onLogout={onLogout} />}>
        <Route index element={<Navigate to="/cockpit" replace />} />
        <Route path="/cockpit" element={<CockpitPage deps={deps} />} />

        {/* Cockpit-Drilldowns (Slice 1, Dispatch B) */}
        <Route path="/cockpit/macro" element={<MacroDrilldown />} />
        <Route path="/cockpit/commodities" element={<CommoditiesDrilldown />} />
        <Route path="/cockpit/sentiment" element={<SentimentDrilldown />} />
        <Route path="/cockpit/yield-curve" element={<YieldCurveDrilldown />} />
        <Route path="/cockpit/sectors" element={<SectorsDrilldown />} />

        {/* Spezial-Widgets (Slice 1, Dispatch C) */}
        <Route path="/cockpit/buffett" element={<BuffettWidget />} />
        <Route path="/cockpit/big-mac" element={<BigMacWidget />} />

        <Route path="/deep-dive" element={<PlaceholderPage title="Deep-Dive — Titel über die Suche oben öffnen" />} />
        <Route path="/deep-dive/:ticker" element={<DeepDivePage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/backtester" element={<PlaceholderPage title="Backtester" />} />
        <Route path="/einstellungen" element={<PlaceholderPage title="Einstellungen" />} />
        <Route path="*" element={<Navigate to="/cockpit" replace />} />
      </Route>
    </Routes>
  );
}
