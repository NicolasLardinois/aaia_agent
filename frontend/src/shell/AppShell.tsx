import { Outlet, useNavigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export interface AppShellProps {
  inboxCount: number;
  onLogout?: () => void;
}

export function AppShell({ inboxCount, onLogout }: AppShellProps) {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen bg-bg text-ink">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar inboxCount={inboxCount} onSearch={(t) => navigate(`/deep-dive/${t}`)} onLogout={onLogout} />
        <main className="mx-auto min-w-0 w-full max-w-6xl flex-1 space-y-5 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
