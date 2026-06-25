import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTheme } from "./useTheme";

export interface TopbarProps {
  inboxCount: number;
  onSearch: (ticker: string) => void;
  onLogout?: () => void;
}

const ICON_BTN =
  "grid h-8 w-8 place-items-center rounded-lg text-muted transition-colors hover:bg-ink/[0.06] hover:text-ink";

export function Topbar({ inboxCount, onSearch, onLogout }: TopbarProps) {
  const { theme, toggle } = useTheme();
  const [q, setQ] = useState("");
  return (
    <header className="flex items-center justify-between gap-4 border-b border-line bg-surface/70 px-4 py-2 backdrop-blur">
      <form
        onSubmit={(e) => { e.preventDefault(); const t = q.trim().toUpperCase(); if (t) onSearch(t); }}
        className="flex-1"
      >
        <div className="relative max-w-md">
          <span aria-hidden className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">⌕</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Titel oder Markt suchen — z. B. AAPL, Gold, EUR"
            aria-label="Ticker oder Markt suchen"
            className="w-full rounded-lg border border-line bg-surface-2 py-1.5 pl-9 pr-3 text-sm text-ink placeholder:text-muted focus:border-brand focus:bg-surface focus:outline-none"
          />
        </div>
      </form>
      <div className="flex items-center gap-1">
        <NavLink to="/willkommen" className={ICON_BTN} aria-label="Hilfe / Willkommen" title="Willkommen & Hilfe">?</NavLink>
        <NavLink to="/inbox" className={`relative ${ICON_BTN}`} aria-label="Inbox" title="Konflikt-Inbox">
          ✉
          {inboxCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-bear px-1 text-[10px] font-semibold text-white">
              {inboxCount}
            </span>
          )}
        </NavLink>
        <button type="button" onClick={toggle} className={ICON_BTN} aria-label="Theme umschalten" title="Hell/Dunkel">
          {theme === "dark" ? "☀" : "◐"}
        </button>
        {onLogout && (
          <button type="button" onClick={onLogout} className="ml-1 rounded-lg px-2 py-1 text-sm text-muted hover:text-ink hover:underline">
            Abmelden
          </button>
        )}
      </div>
    </header>
  );
}
