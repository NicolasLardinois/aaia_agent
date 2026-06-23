import { NavLink } from "react-router-dom";

const ITEMS: { to: string; label: string; icon: string }[] = [
  { to: "/cockpit", label: "Cockpit", icon: "▣" },
  { to: "/deep-dive", label: "Deep-Dive", icon: "◆" },
  { to: "/portfolio", label: "Portfolio", icon: "⬚" },
  { to: "/inbox", label: "Inbox", icon: "✉" },
  { to: "/backtester", label: "Backtester", icon: "↺" },
  { to: "/einstellungen", label: "Einstellungen", icon: "⚙" },
];

export function Sidebar() {
  return (
    <nav className="flex w-48 shrink-0 flex-col gap-1 border-r border-slate-200 p-3 dark:border-slate-700">
      <div className="px-2 pb-2 text-lg font-bold">AAIA</div>
      {ITEMS.map((it) => (
        <NavLink
          key={it.to}
          to={it.to}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded px-2 py-1.5 text-sm ${
              isActive ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            }`
          }
        >
          <span aria-hidden>{it.icon}</span>{it.label}
        </NavLink>
      ))}
    </nav>
  );
}
