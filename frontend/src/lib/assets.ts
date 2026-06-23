import type { Underlying, Wrapper } from "../contract/common";

export interface BadgeVisual {
  label: string;
  icon: string;
  colorClass: string;
}

// Basiswert (underlying) -> Anzeige. Material-/Form-Icon je Anlageklasse (Konzept §5.2).
export function underlyingToVisual(u: Underlying): BadgeVisual {
  switch (u) {
    case "equity":         return { label: "Aktie",     icon: "🏢", colorClass: "bg-sky-100 text-sky-800" };
    case "equity_index":   return { label: "Index",     icon: "📈", colorClass: "bg-indigo-100 text-indigo-800" };
    case "bond":           return { label: "Anleihe",   icon: "🏛", colorClass: "bg-emerald-100 text-emerald-800" };
    case "commodity":      return { label: "Rohstoff",  icon: "🛢", colorClass: "bg-amber-100 text-amber-800" };
    case "precious_metal": return { label: "Edelmetall", icon: "🥇", colorClass: "bg-yellow-100 text-yellow-800" };
  }
}

// Huelle (wrapper) -> Anzeige.
export function wrapperToVisual(w: Wrapper): BadgeVisual {
  switch (w) {
    case "single":       return { label: "Einzeltitel",   icon: "•",  colorClass: "bg-slate-100 text-slate-700" };
    case "fund":         return { label: "Fonds",         icon: "▣",  colorClass: "bg-slate-100 text-slate-700" };
    case "future":       return { label: "Future",        icon: "⏳", colorClass: "bg-orange-100 text-orange-800" };
    case "physical_etc": return { label: "Physisch (ETC)", icon: "⛃", colorClass: "bg-slate-100 text-slate-700" };
  }
}
