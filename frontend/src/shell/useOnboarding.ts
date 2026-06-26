// "Willkommen schon gesehen?"-Flag, persistiert in localStorage (Muster wie useAuth/useTheme).
import { useCallback, useState } from "react";

const KEY = "aaia_onboarding_seen";

export function useOnboarding() {
  const [seen, setSeen] = useState<boolean>(() => {
    try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
  });
  const markSeen = useCallback(() => {
    try { localStorage.setItem(KEY, "1"); } catch { /* localStorage nicht verfügbar -> ignorieren */ }
    setSeen(true);
  }, []);
  // Setzt das Flag zurueck -> die Willkommen-/Einfuehrungs-Seite erscheint wieder
  // (Einstellungen-Seite, Mangel #8: "Einfuehrung erneut anzeigen").
  const reset = useCallback(() => {
    try { localStorage.removeItem(KEY); } catch { /* ignorieren */ }
    setSeen(false);
  }, []);
  return { seen, markSeen, reset };
}
