import { describe, it, expect } from "vitest";
import { periodChange } from "./priceSeries";

describe("periodChange", () => {
  it("steigender Verlauf -> positive Veraenderung, Richtung up", () => {
    const c = periodChange([
      { date: "2026-01-01", close: 100 },
      { date: "2026-02-01", close: 110 },
      { date: "2026-03-01", close: 120 },
    ]);
    expect(c.absolute).toBe(20);
    expect(c.pct).toBe(20);          // (120-100)/100*100
    expect(c.direction).toBe("up");
  });

  it("fallender Verlauf -> negative Veraenderung, Richtung down", () => {
    const c = periodChange([
      { date: "2026-01-01", close: 200 },
      { date: "2026-02-01", close: 150 },
    ]);
    expect(c.absolute).toBe(-50);
    expect(c.pct).toBe(-25);
    expect(c.direction).toBe("down");
  });

  it("unveraenderter Verlauf -> flat", () => {
    const c = periodChange([
      { date: "2026-01-01", close: 100 },
      { date: "2026-02-01", close: 100 },
    ]);
    expect(c.absolute).toBe(0);
    expect(c.pct).toBe(0);
    expect(c.direction).toBe("flat");
  });

  it("leere oder einzelne Reihe -> neutraler Nullwert (kein Crash, keine Division durch 0)", () => {
    expect(periodChange([])).toEqual({ absolute: 0, pct: 0, direction: "flat" });
    expect(periodChange([{ date: "2026-01-01", close: 100 }])).toEqual({ absolute: 0, pct: 0, direction: "flat" });
  });
});
