import { describe, it, expect } from "vitest";
import { combineValuationRange, valuationPosition } from "./valuationRange";
import type { ValuationMethodDTO } from "../contract/deepdive";

const m = (name: string, low: number, high: number): ValuationMethodDTO => ({ name, low, high });

describe("combineValuationRange", () => {
  it("liefert null bei leerer Methodenliste", () => {
    expect(combineValuationRange([])).toBeNull();
  });
  it("nimmt bei einer Methode genau deren Band", () => {
    expect(combineValuationRange([m("DCF", 100, 140)])).toEqual({ low: 100, high: 140 });
  });
  it("nimmt den Median der lows/highs (kein kuenstlich breites min/max-Band)", () => {
    // lows 90/100/120 -> Median 100; highs 130/150/170 -> Median 150
    const out = combineValuationRange([m("KGV", 90, 130), m("EV", 100, 150), m("DCF", 120, 170)]);
    expect(out).toEqual({ low: 100, high: 150 });
  });
});

describe("valuationPosition", () => {
  it("unter 0.95*low => undervalued (BULLISH-Seite)", () => {
    expect(valuationPosition(90, 100, 150)).toBe("undervalued"); // 90 < 95
  });
  it("ueber 1.05*high => overvalued (BEARISH-Seite)", () => {
    expect(valuationPosition(160, 100, 150)).toBe("overvalued"); // 160 > 157.5
  });
  it("genau im Band => fair", () => {
    expect(valuationPosition(125, 100, 150)).toBe("fair");
  });
  it("knapp innerhalb der 5%-Toleranz => fair (Grenzfall)", () => {
    expect(valuationPosition(96, 100, 150)).toBe("fair");   // 96 >= 95
    expect(valuationPosition(157, 100, 150)).toBe("fair");  // 157 <= 157.5
  });
});
