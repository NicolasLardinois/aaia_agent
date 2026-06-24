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
    <div className="flex min-h-screen bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar inboxCount={inboxCount} onSearch={(t) => navigate(`/deep-dive/${t}`)} onLogout={onLogout} />
        <main className="min-w-0 flex-1 space-y-4 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
