// Semantische Icon-Schicht (Konzept: Indirektion wie ein Port).
// Die App referenziert Icons ueber STABILE semantische Namen — nicht direkt ueber
// lucide-Komponenten. Vorteil: ein Austausch des Icon-Sets passiert nur hier, und
// reine lib/-Module brauchen nur den IconName-TYP (kein React/lucide-Import).
import {
  // Navigation
  Home, LayoutDashboard, Telescope, Briefcase, Inbox, History, Settings,
  // Basiswerte (underlying)
  Building2, TrendingUp, TrendingDown, Landmark, Fuel, Gem,
  // Huellen (wrapper)
  Circle, Layers, CalendarClock, Package,
  // Status / UI-Chrome
  AlertTriangle, Check, X, ChevronUp, ChevronDown, ChevronRight, ChevronsUpDown,
  Table, Map, ArrowLeft, ArrowRight, ArrowLeftRight,
  // Topbar
  Search, HelpCircle, Sun, Moon,
  // Einstellungen
  Monitor, LogOut,
  // Cockpit-Synthese
  Activity, Compass,
  type LucideIcon,
} from "lucide-react";

// Eine stabile Namens-Quelle. lib/-Module importieren NUR diesen Typ (type-only),
// damit dort kein React/lucide landet.
export type IconName =
  | "nav-welcome" | "nav-cockpit" | "nav-deepdive" | "nav-portfolio"
  | "nav-inbox" | "nav-backtester" | "nav-settings"
  | "asset-equity" | "asset-index" | "asset-bond" | "asset-commodity" | "asset-precious-metal"
  | "trend-up" | "trend-down"
  | "wrap-single" | "wrap-fund" | "wrap-future" | "wrap-physical"
  | "warning" | "check" | "cross"
  | "sort-asc" | "sort-desc" | "sort-none"
  | "view-table" | "view-map" | "arrow-left" | "arrow-right" | "compare"
  | "search" | "help" | "theme-light" | "theme-dark" | "theme-system"
  | "logout"
  | "pulse" | "compass"
  | "disclosure-open" | "disclosure-closed";

// Registry: semantischer Name -> lucide-Komponente. Record erzwingt Vollstaendigkeit
// schon zur Compile-Zeit (jeder IconName MUSS ein Icon haben).
const ICONS: Record<IconName, LucideIcon> = {
  "nav-welcome": Home,
  "nav-cockpit": LayoutDashboard,
  "nav-deepdive": Telescope,
  "nav-portfolio": Briefcase,
  "nav-inbox": Inbox,
  "nav-backtester": History,
  "nav-settings": Settings,
  "asset-equity": Building2,
  "asset-index": TrendingUp,
  "asset-bond": Landmark,
  "asset-commodity": Fuel,
  "asset-precious-metal": Gem,
  "trend-up": TrendingUp,
  "trend-down": TrendingDown,
  "wrap-single": Circle,
  "wrap-fund": Layers,
  "wrap-future": CalendarClock,
  "wrap-physical": Package,
  warning: AlertTriangle,
  check: Check,
  cross: X,
  "sort-asc": ChevronUp,
  "sort-desc": ChevronDown,
  "sort-none": ChevronsUpDown,
  "view-table": Table,
  "view-map": Map,
  "arrow-left": ArrowLeft,
  "arrow-right": ArrowRight,
  compare: ArrowLeftRight,
  search: Search,
  help: HelpCircle,
  "theme-light": Sun,
  "theme-dark": Moon,
  "theme-system": Monitor,
  logout: LogOut,
  pulse: Activity,
  compass: Compass,
  "disclosure-open": ChevronDown,
  "disclosure-closed": ChevronRight,
};

// Laufzeit-Liste aller Namen (fuer den Vollstaendigkeits-Test).
export const ICON_NAMES = Object.keys(ICONS) as IconName[];

export interface IconProps {
  name: IconName;
  /** Wenn gesetzt: Icon traegt Bedeutung -> role=img + aria-label (Screenreader liest es).
   *  Wenn leer: rein dekorativ -> aria-hidden (der danebenstehende Text traegt die Bedeutung). */
  label?: string;
  /** Tailwind-Groesse/Farbe; Default h-4 w-4 = 16px, passt zur Body-Zeile. */
  className?: string;
  strokeWidth?: number;
}

export function Icon({ name, label, className, strokeWidth = 2 }: IconProps) {
  const LucideCmp = ICONS[name];
  const decorative = label === undefined || label === "";
  return (
    <LucideCmp
      className={className ?? "h-4 w-4"}
      strokeWidth={strokeWidth}
      aria-hidden={decorative ? true : undefined}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : label}
    />
  );
}
