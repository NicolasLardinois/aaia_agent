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
});

describe("leverageFactor", () => {
  it("Hebel = Nominalwert / Margin", () => {
    expect(leverageFactor(236000, 7150)).toBeCloseTo(33.0, 0);
  });
  it("Margin 0 => 0 (kein Division-durch-Null-Absturz)", () => {
    expect(leverageFactor(1000, 0)).toBe(0);
  });
});
