import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./shell/AppShell";
import { CockpitPage } from "./pages/CockpitPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { MacroDrilldown } from "./pages/cockpit/MacroDrilldown";
import { CommoditiesDrilldown } from "./pages/cockpit/CommoditiesDrilldown";
import { SentimentDrilldown } from "./pages/cockpit/SentimentDrilldown";
import { YieldCurveDrilldown } from "./pages/cockpit/YieldCurveDrilldown";
import { SectorsDrilldown } from "./pages/cockpit/SectorsDrilldown";
import type { UseCockpitDeps } from "./hooks/useCockpit";

// Routen unter der Shell. Inbox-Anzahl ist in Slice 0 noch 0 (Slice 4 speist sie).
// Drilldown-Routen (B7): /cockpit/<domain> -> jeweilige Drilldown-Seite.
// Buffett (/cockpit/buffett) und Big-Mac (/cockpit/big-mac) werden in Dispatch C ergaenzt.
export function AppRoutes({ deps, onLogout }: { deps?: UseCockpitDeps; onLogout?: () => void }) {
  return (
    <Routes>
      <Route element={<AppShell inboxCount={0} onLogout={onLogout} />}>
        <Route index element={<Navigate to="/cockpit" replace />} />
        <Route path="/cockpit" element={<CockpitPage deps={deps} />} />

        {/* Cockpit-Drilldowns (Slice 1, Dispatch B) */}
        <Route path="/cockpit/macro" element={<MacroDrilldown />} />
        <Route path="/cockpit/commodities" element={<CommoditiesDrilldown />} />
        <Route path="/cockpit/sentiment" element={<SentimentDrilldown />} />
        <Route path="/cockpit/yield-curve" element={<YieldCurveDrilldown />} />
        <Route path="/cockpit/sectors" element={<SectorsDrilldown />} />

        {/* Platzhalter fuer Dispatch C (Buffett, Big-Mac) */}
        <Route path="/cockpit/buffett" element={<PlaceholderPage title="Buffett-Indikator" />} />
        <Route path="/cockpit/big-mac" element={<PlaceholderPage title="Big-Mac-Index" />} />

        <Route path="/deep-dive" element={<PlaceholderPage title="Deep-Dive — Titel über die Suche oben öffnen" />} />
        <Route path="/deep-dive/:ticker" element={<PlaceholderPage title="Deep-Dive" />} />
        <Route path="/portfolio" element={<PlaceholderPage title="Portfolio" />} />
        <Route path="/inbox" element={<PlaceholderPage title="Inbox" />} />
        <Route path="/backtester" element={<PlaceholderPage title="Backtester" />} />
        <Route path="/einstellungen" element={<PlaceholderPage title="Einstellungen" />} />
        <Route path="*" element={<Navigate to="/cockpit" replace />} />
      </Route>
    </Routes>
  );
}
