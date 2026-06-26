// React-Anbindung an lib/preferences: liefert die aktuellen Praeferenzen + einen Setter
// und haelt alle Komponenten ueber den Event-Bus synchron (Topbar-Theme-Toggle UND
// Einstellungen-Seite zeigen denselben Stand). Wendet die Praeferenzen beim Mount an.
import { useCallback, useEffect, useState } from "react";
import {
  readPreferences, writePreference, applyPreferences, subscribePreferences,
  type Preferences,
} from "../lib/preferences";

export function usePreferences() {
  const [prefs, setPrefs] = useState<Preferences>(() => readPreferences());

  useEffect(() => {
    applyPreferences(readPreferences());                         // Stand beim Mount auf <html> spiegeln
    return subscribePreferences(() => setPrefs(readPreferences())); // bei jeder Aenderung neu lesen
  }, []);

  const set = useCallback(
    <K extends keyof Preferences>(key: K, value: Preferences[K]) => writePreference(key, value),
    [],
  );

  return { prefs, set };
}
