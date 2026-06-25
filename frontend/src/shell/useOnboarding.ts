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
  return { seen, markSeen };
}
