import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTheme } from "./useTheme";

export interface TopbarProps {
  inboxCount: number;
  onSearch: (ticker: string) => void;
  onLogout?: () => void;
}

export function Topbar({ inboxCount, onSearch, onLogout }: TopbarProps) {
  const { theme, toggle } = useTheme();
  const [q, setQ] = useState("");
  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-200 px-4 py-2 dark:border-slate-700">
      <form
        onSubmit={(e) => { e.preventDefault(); const t = q.trim().toUpperCase(); if (t) onSearch(t); }}
        className="flex-1"
      >
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="z. B. AAPL, Gold, EUR …"
          aria-label="Ticker oder Markt suchen"
          className="w-full max-w-md rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </form>
      <div className="flex items-center gap-3">
        <NavLink to="/inbox" className="relative text-sm" aria-label="Inbox">
          ✉
          {inboxCount > 0 && (
            <span className="absolute -right-3 -top-2 rounded-full bg-red-600 px-1.5 text-xs text-white">{inboxCount}</span>
          )}
        </NavLink>
        <button type="button" onClick={toggle} className="text-sm" aria-label="Theme umschalten">
          {theme === "dark" ? "☀" : "◐"}
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout} className="text-sm text-slate-500 underline">Abmelden</button>
        )}
      </div>
    </header>
  );
}
