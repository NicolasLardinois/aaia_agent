import "@testing-library/jest-dom";

// Node 26 + jsdom stellen kein funktionierendes localStorage bereit -> minimaler,
// korrekter Map-basierter Ersatz fuer Tests (nur falls nicht vorhanden).
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  globalThis.localStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => { store.set(k, String(v)); },
    removeItem: (k: string) => { store.delete(k); },
    clear: () => { store.clear(); },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() { return store.size; },
  } as Storage;
}
