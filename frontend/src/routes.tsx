import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./shell/AppShell";
import { CockpitPage } from "./pages/CockpitPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import type { UseCockpitDeps } from "./hooks/useCockpit";

// Routen unter der Shell. Inbox-Anzahl ist in Slice 0 noch 0 (Slice 4 speist sie).
export function AppRoutes({ deps, onLogout }: { deps?: UseCockpitDeps; onLogout?: () => void }) {
  return (
    <Routes>
      <Route element={<AppShell inboxCount={0} onLogout={onLogout} />}>
        <Route index element={<Navigate to="/cockpit" replace />} />
        <Route path="/cockpit" element={<CockpitPage deps={deps} />} />
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
