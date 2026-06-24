import { describe, it, expect } from "vitest";
import { rollYieldVisual, leverageFactor } from "./futures";

describe("rollYieldVisual", () => {
  it("Contango => Gegenwind, negativ, Abwaerts-Pfeil (Roll-Yield<0)", () => {
    const v = rollYieldVisual(-3.1, "contango");
    expect(v.arrow).toBe("▼");
    expect(v.colorClass).toContain("red");
    expect(v.label).toMatch(/Gegenwind/i);
  });
  it("Backwardation => Rueckenwind, positiv, Aufwaerts-Pfeil", () => {
    const v = rollYieldVisual(2.4, "backwardation");
    expect(v.arrow).toBe("▲");
    expect(v.colorClass).toContain("green");
    expect(v.label).toMatch(/Rueckenwind|Rückenwind/i);
  });
  it("Kurvenform-Name kommt aus dem form-Argument, nicht aus dem Vorzeichen", () => {
    // Inkonsistenter Fall (z. B. Misch-/Uebergangskurve): Roll-Yield negativ,
    // Form aber als backwardation gemeldet -> die Form im Label muss der gemeldeten
    // Form folgen, nicht dem Vorzeichen (sonst stilles Mislabel, AGENTS.md §3).
    const v = rollYieldVisual(-1.0, "backwardation");
    expect(v.label).toMatch(/Backwardation/i);
    expect(v.label).not.toMatch(/Contango/i);
  });
  it("flache Kurve => neutral, Form als 'flach' benannt", () => {
    const v = rollYieldVisual(0, "flat");
    expect(v.arrow).toBe("→");
    expect(v.label).toMatch(/flach/i);
  });
});

describe("leverageFactor", () => {
  it("Hebel = Nominalwert / Margin", () => {
    expect(leverageFactor(236000, 7150)).toBeCloseTo(33.0, 0);
  });
  it("Margin 0 => 0 (kein Division-durch-Null-Absturz)", () => {
    expect(leverageFactor(1000, 0)).toBe(0);
  });
});
