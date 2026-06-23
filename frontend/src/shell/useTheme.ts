import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "aaia_theme";

// Hell/Dunkel-Umschalter; persistiert und steuert die Tailwind-'dark'-Klasse am <html>.
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(KEY) as Theme) || "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = useCallback(() => setTheme((t) => (t === "light" ? "dark" : "light")), []);
  return { theme, toggle };
}
