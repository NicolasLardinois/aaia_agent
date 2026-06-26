// Nutzer-Praeferenzen (Einstellungen-Seite, Mangel #8). Rein client-seitig, in
// localStorage persistiert — Muster wie useTheme/useOnboarding, aber an EINER Stelle
// gebuendelt: Lesen/Schreiben/Anwenden + ein winziger Event-Bus, damit mehrere
// Komponenten (Topbar-Theme-Toggle UND die Einstellungen-Seite) synchron bleiben.
// Diese Datei ist die Seiteneffekt-Grenze (localStorage, document, matchMedia).

export type ThemeMode = "light" | "dark" | "system";
export type MotionMode = "system" | "reduce";
export type StartView = "/cockpit" | "/portfolio" | "/backtester";

export interface Preferences {
  theme: ThemeMode;
  motion: MotionMode;
  startView: StartView;
}

// Default: Theme + Bewegung folgen dem Betriebssystem (modernes, respektvolles Verhalten);
// Start-Ansicht ist das Cockpit (das bisherige Standardziel).
export const DEFAULT_PREFERENCES: Preferences = { theme: "system", motion: "system", startView: "/cockpit" };

const THEME_KEY = "aaia_theme";        // teilt sich den Schluessel mit dem alten useTheme (abwaertskompatibel)
const MOTION_KEY = "aaia_motion";
const START_KEY = "aaia_start_view";

const THEME_MODES: ThemeMode[] = ["light", "dark", "system"];
const MOTION_MODES: MotionMode[] = ["system", "reduce"];
const START_VIEWS: StartView[] = ["/cockpit", "/portfolio", "/backtester"];

const KEY_OF: Record<keyof Preferences, string> = { theme: THEME_KEY, motion: MOTION_KEY, startView: START_KEY };

// Liest einen Wert nur, wenn er in der erlaubten Menge liegt — sonst Default (verhindert
// kaputte/manipulierte localStorage-Werte, die sonst die UI in einen ungueltigen Zustand braechten).
function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key) as T | null;
    return v && (allowed as readonly string[]).includes(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

export function readPreferences(): Preferences {
  return {
    theme: read(THEME_KEY, THEME_MODES, DEFAULT_PREFERENCES.theme),
    motion: read(MOTION_KEY, MOTION_MODES, DEFAULT_PREFERENCES.motion),
    startView: read(START_KEY, START_VIEWS, DEFAULT_PREFERENCES.startView),
  };
}

function media(query: string): MediaQueryList | null {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia(query) : null;
}

/** Effektives Hell/Dunkel: explizit gewinnt, 'system' folgt der OS-Praeferenz. */
export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "light" || mode === "dark") return mode;
  return media("(prefers-color-scheme: dark)")?.matches ? "dark" : "light";
}

/** Effektive Bewegungsreduktion: 'reduce' erzwingt, 'system' folgt der OS-Praeferenz. */
export function resolveReducedMotion(mode: MotionMode): boolean {
  if (mode === "reduce") return true;
  return media("(prefers-reduced-motion: reduce)")?.matches ?? false;
}

/** Wendet die Praeferenzen auf <html> an: 'dark'-Klasse + data-reduce-motion. */
export function applyPreferences(prefs: Preferences = readPreferences()): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", resolveTheme(prefs.theme) === "dark");
  if (resolveReducedMotion(prefs.motion)) root.dataset.reduceMotion = "reduce";
  else delete root.dataset.reduceMotion;
}

// --- winziger Event-Bus (Beobachter), damit alle Komponenten synchron bleiben ---
type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribePreferences(cb: Listener): () => void {
  listeners.add(cb);
  return () => { listeners.delete(cb); };
}

/** Schreibt eine Praeferenz, wendet sie sofort an und benachrichtigt alle Abonnenten. */
export function writePreference<K extends keyof Preferences>(key: K, value: Preferences[K]): void {
  try { localStorage.setItem(KEY_OF[key], value); } catch { /* localStorage nicht verfuegbar -> ignorieren */ }
  applyPreferences(readPreferences());
  for (const l of listeners) l();
}
