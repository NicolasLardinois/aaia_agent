import { describe, it, expect } from "vitest";
import { CHART, themedGrid, themedAxis, themedTooltip, areaGradient } from "./chartTheme";

describe("chartTheme", () => {
  it("haelt die Signal-/Marken-Farben passend zu den Design-Tokens", () => {
    // Finanzsemantik: bull gruen, bear rot, neutral grau, Marke Kobalt-Indigo.
    expect(CHART.brand).toBe("#4f5bd5");
    expect(CHART.bull).toBe("#0e9f6e");
    expect(CHART.bear).toBe("#e5484d");
    expect(CHART.neutral).toBe("#8a93a3");
  });

  it("Achsen nutzen die gedaempfte Label-Farbe und dezente Splitlines", () => {
    const ax = themedAxis("value");
    expect(ax.type).toBe("value");
    expect(ax.axisLabel.color).toBe(CHART.axisLabel);
    // Splitlines sollen dezent (halbtransparent) sein -> auf hell UND dunkel lesbar
    expect(ax.splitLine.lineStyle.color).toContain("rgba");
  });

  it("Grid laesst Raum fuer Achsen und nutzt containLabel", () => {
    const g = themedGrid();
    expect(g.containLabel).toBe(true);
  });

  it("Tooltip uebernimmt den uebergebenen Trigger", () => {
    expect(themedTooltip("axis").trigger).toBe("axis");
    expect(themedTooltip("item").trigger).toBe("item");
  });

  it("areaGradient legt die Farbe oben deckend, unten transparent an (Flaeche unter der Linie)", () => {
    const grad = areaGradient("#0e9f6e");
    // ECharts-LinearGradient-Form; Farbe als rgba(14,159,110,..) gespiegelt
    expect(grad.type).toBe("linear");
    expect(grad.colorStops[0].color).toContain("14,159,110");  // RGB von #0e9f6e, oben halbtransparent
    // unterer Stop voll transparent (Alpha 0)
    expect(grad.colorStops[grad.colorStops.length - 1].color).toMatch(/,0\)$/);
  });
});
