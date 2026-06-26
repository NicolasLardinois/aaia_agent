import { describe, it, expect } from "vitest";
import { TICKER_UNIVERSE } from "./tickerUniverse";
import { demoDeepDive } from "./demo/deepdive";

describe("TICKER_UNIVERSE", () => {
  it("enthält ein sinnvoll großes Universum (Bug #10: größer als nur die Demo-6)", () => {
    expect(TICKER_UNIVERSE.length).toBeGreaterThanOrEqual(12);
  });

  it("hat eindeutige, nicht-leere Symbole und Namen", () => {
    const seen = new Set<string>();
    for (const e of TICKER_UNIVERSE) {
      expect(e.ticker.trim()).not.toBe("");
      expect(e.name.trim()).not.toBe("");
      expect(seen.has(e.ticker), `Doppeltes Symbol: ${e.ticker}`).toBe(false);
      seen.add(e.ticker);
    }
  });

  it("führt Aliasse als nicht-leere Strings (für die Synonym-Suche)", () => {
    for (const e of TICKER_UNIVERSE) {
      expect(Array.isArray(e.aliases)).toBe(true);
      for (const a of e.aliases) expect(a.trim()).not.toBe("");
    }
  });

  it("ist für jedes Symbol als Demo-Deep-Dive ladbar (kein Vorschlag führt ins Leere)", () => {
    for (const e of TICKER_UNIVERSE) {
      const view = demoDeepDive(e.ticker);
      expect(view.found, `Universum-Ticker nicht ladbar: ${e.ticker}`).toBe(true);
      expect(view.ticker).toBe(e.ticker);
    }
  });
});
