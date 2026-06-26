import { useCallback } from "react";
import { usePreferences } from "./usePreferences";
import { resolveTheme } from "../lib/preferences";

export type Theme = "light" | "dark";

// Hell/Dunkel-Umschalter fuer die Topbar — jetzt nur noch eine duenne Schicht ueber den
// gemeinsamen Praeferenzen (lib/preferences). 'theme' ist das EFFEKTIVE Hell/Dunkel
// (loest 'system' auf), 'toggle' schaltet explizit auf das Gegenteil. So bleiben Topbar
// und Einstellungen-Seite synchron.
export function useTheme(): { theme: Theme; toggle: () => void } {
  const { prefs, set } = usePreferences();
  const theme = resolveTheme(prefs.theme);
  const toggle = useCallback(() => set("theme", theme === "dark" ? "light" : "dark"), [theme, set]);
  return { theme, toggle };
}
