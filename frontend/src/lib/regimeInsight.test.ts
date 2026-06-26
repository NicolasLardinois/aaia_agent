import { describe, it, expect } from "vitest";
import { regimeInsight, REGIME_KEYS } from "./regimeInsight";

describe("regimeInsight", () => {
  it("kennt alle sechs Konjunktur-Phasen mit gefuelltem Inhalt", () => {
    for (const key of REGIME_KEYS) {
      const i = regimeInsight(key);
      expect(i.summary.length).toBeGreaterThan(0);
      expect(i.favored.length).toBeGreaterThan(0);
      expect(i.caution.length).toBeGreaterThan(0);
      expect(i.known).toBe(true);
    }
  });

  it("deutet Aufschwung als risikofreundlich (Aktien fuehren)", () => {
    const i = regimeInsight("Aufschwung");
    expect(i.favored).toMatch(/Aktien|zyklisch/i);
  });

  it("deutet Rezession defensiv (Anleihen/Cash vorn)", () => {
    const i = regimeInsight("Rezession");
    expect(i.favored).toMatch(/Anleihen|Cash/i);
  });

  it("ist gross-/kleinschreibungs-unabhaengig", () => {
    expect(regimeInsight("AUFSCHWUNG").summary).toBe(regimeInsight("Aufschwung").summary);
    expect(regimeInsight("  rezession  ").summary).toBe(regimeInsight("Rezession").summary);
  });

  it("faellt bei unbekanntem Regime auf einen neutralen Hinweis zurueck (known=false)", () => {
    const i = regimeInsight("Foobar");
    expect(i.known).toBe(false);
    expect(i.summary.length).toBeGreaterThan(0);
  });
});
