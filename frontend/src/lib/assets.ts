import type { Underlying, Wrapper } from "../contract/common";
import type { IconName } from "../components/icons";

export interface BadgeVisual {
  label: string;
  icon: IconName;   // semantischer Icon-Name (rendert via <Icon>), nicht mehr Emoji
  colorClass: string;
}

// Basiswert (underlying) -> Anzeige. Semantisches Icon je Anlageklasse (Konzept §5.2).
export function underlyingToVisual(u: Underlying): BadgeVisual {
  switch (u) {
    case "equity":         return { label: "Aktie",      icon: "asset-equity",         colorClass: "bg-sky-100 text-sky-800" };
    case "equity_index":   return { label: "Index",      icon: "asset-index",          colorClass: "bg-indigo-100 text-indigo-800" };
    case "bond":           return { label: "Anleihe",    icon: "asset-bond",           colorClass: "bg-emerald-100 text-emerald-800" };
    case "commodity":      return { label: "Rohstoff",   icon: "asset-commodity",      colorClass: "bg-amber-100 text-amber-800" };
    case "precious_metal": return { label: "Edelmetall", icon: "asset-precious-metal", colorClass: "bg-yellow-100 text-yellow-800" };
  }
}

// Huelle (wrapper) -> Anzeige.
export function wrapperToVisual(w: Wrapper): BadgeVisual {
  switch (w) {
    case "single":       return { label: "Einzeltitel",    icon: "wrap-single",   colorClass: "bg-slate-100 text-slate-700" };
    case "fund":         return { label: "Fonds",          icon: "wrap-fund",     colorClass: "bg-slate-100 text-slate-700" };
    case "future":       return { label: "Future",         icon: "wrap-future",   colorClass: "bg-orange-100 text-orange-800" };
    case "physical_etc": return { label: "Physisch (ETC)", icon: "wrap-physical", colorClass: "bg-slate-100 text-slate-700" };
  }
}
