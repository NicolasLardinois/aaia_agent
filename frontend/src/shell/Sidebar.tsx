import { NavLink } from "react-router-dom";
import { Icon } from "../components/icons";
import type { IconName } from "../components/icons";

const ITEMS: { to: string; label: string; icon: IconName }[] = [
  { to: "/willkommen", label: "Willkommen", icon: "nav-welcome" },
  { to: "/cockpit", label: "Cockpit", icon: "nav-cockpit" },
  { to: "/deep-dive", label: "Deep-Dive", icon: "nav-deepdive" },
  { to: "/portfolio", label: "Portfolio", icon: "nav-portfolio" },
  { to: "/inbox", label: "Inbox", icon: "nav-inbox" },
  { to: "/backtester", label: "Backtester", icon: "nav-backtester" },
  { to: "/einstellungen", label: "Einstellungen", icon: "nav-settings" },
];

export function Sidebar() {
  return (
    <nav className="flex w-52 shrink-0 flex-col gap-1 border-r border-line bg-surface-2/60 p-3">
      {/* Markenzeichen: Wortmarke in der Display-Schrift + Cockpit-Signet */}
      <div className="mb-4 flex items-center gap-2 px-1 pt-1">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-brand font-display text-sm font-bold text-brand-ink">A</span>
        <span className="font-display text-lg font-bold tracking-tight">AAIA</span>
      </div>
      <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Navigation</div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          className={({ isActive }) =>
            `flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors ${
              isActive
                ? "bg-brand/10 font-medium text-brand"
                : "text-muted hover:bg-ink/[0.05] hover:text-ink"
            }`
          }
        >
          <Icon name={it.icon} className="h-[1.05rem] w-[1.05rem] shrink-0 opacity-80" />
          {it.label}
        </NavLink>
      ))}
      <div className="mt-auto px-2 pt-4 text-[10px] leading-relaxed text-muted">
        AAIA · v1<br />Demo-Daten möglich
      </div>
    </nav>
  );
}
