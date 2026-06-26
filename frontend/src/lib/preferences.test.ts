import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  readPreferences, writePreference, applyPreferences,
  resolveTheme, resolveReducedMotion, subscribePreferences, DEFAULT_PREFERENCES,
} from "./preferences";

// Hilfs-Stub: window.matchMedia so faken, dass eine bestimmte Query "matcht".
function stubMatchMedia(matching: (query: string) => boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: matching(query),
    media: query,
    addEventListener: () => {}, removeEventListener: () => {},
    addListener: () => {}, removeListener: () => {}, onchange: null, dispatchEvent: () => false,
  }));
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  delete document.documentElement.dataset.reduceMotion;
});
afterEach(() => vi.unstubAllGlobals());

describe("preferences", () => {
  it("liefert die Defaults bei leerem Speicher", () => {
    expect(readPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  it("ignoriert ungültige gespeicherte Werte und fällt auf den Default zurück", () => {
    localStorage.setItem("aaia_theme", "lila");
    localStorage.setItem("aaia_start_view", "/hack");
    expect(readPreferences().theme).toBe(DEFAULT_PREFERENCES.theme);
    expect(readPreferences().startView).toBe(DEFAULT_PREFERENCES.startView);
  });

  it("persistiert eine Präferenz und wendet sie auf <html> an", () => {
    writePreference("theme", "dark");
    expect(localStorage.getItem("aaia_theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("resolveTheme: explizit gewinnt, 'system' folgt der OS-Präferenz", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
    stubMatchMedia((q) => q.includes("dark")); // OS = dunkel
    expect(resolveTheme("system")).toBe("dark");
    stubMatchMedia(() => false); // OS = hell
    expect(resolveTheme("system")).toBe("light");
  });

  it("resolveReducedMotion: 'reduce' erzwingt, 'system' folgt der OS-Präferenz", () => {
    expect(resolveReducedMotion("reduce")).toBe(true);
    stubMatchMedia((q) => q.includes("reduced-motion"));
    expect(resolveReducedMotion("system")).toBe(true);
    stubMatchMedia(() => false);
    expect(resolveReducedMotion("system")).toBe(false);
  });

  it("applyPreferences setzt data-reduce-motion nur bei erzwungener Reduktion", () => {
    applyPreferences({ theme: "light", motion: "reduce", startView: "/cockpit" });
    expect(document.documentElement.dataset.reduceMotion).toBe("reduce");
    applyPreferences({ theme: "light", motion: "system", startView: "/cockpit" });
    expect(document.documentElement.dataset.reduceMotion).toBeUndefined();
  });

  it("benachrichtigt Abonnenten bei jeder Änderung", () => {
    const cb = vi.fn();
    const unsub = subscribePreferences(cb);
    writePreference("startView", "/portfolio");
    expect(cb).toHaveBeenCalledTimes(1);
    unsub();
    writePreference("startView", "/cockpit");
    expect(cb).toHaveBeenCalledTimes(1); // nach unsub keine weitere Meldung
  });
});
