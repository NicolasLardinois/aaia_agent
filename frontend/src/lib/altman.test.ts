import { describe, it, expect } from "vitest";
import { altmanClass } from "./altman";

describe("altmanClass", () => {
  it("null => unavailable (nie als 0/neutral werten)", () => {
    expect(altmanClass(null, "Technology")).toBe("unavailable");
  });
  it("Financials => not_applicable (Z nicht definiert)", () => {
    expect(altmanClass(3.5, "Banks")).toBe("not_applicable");
  });
  // Manufacturing-naher Sektor -> Original-Z (safe>2.99, distress<1.81)
  it("Manufacturing: 3.0 > 2.99 => safe", () => {
    expect(altmanClass(3.0, "Industrials")).toBe("safe");
  });
  it("Manufacturing: genau 2.99 => grey (strikt groesser fuer safe)", () => {
    expect(altmanClass(2.99, "Industrials")).toBe("grey");
  });
  it("Manufacturing: 1.5 < 1.81 => distress", () => {
    expect(altmanClass(1.5, "Materials")).toBe("distress");
  });
  // Nicht-Manufacturing (Z''): safe>2.6, distress<1.1
  it("Dienstleister: 2.7 > 2.6 => safe", () => {
    expect(altmanClass(2.7, "Technology")).toBe("safe");
  });
  it("Dienstleister: 1.0 < 1.1 => distress", () => {
    expect(altmanClass(1.0, "Technology")).toBe("distress");
  });
  it("Dienstleister: 2.0 zwischen 1.1 und 2.6 => grey", () => {
    expect(altmanClass(2.0, "Technology")).toBe("grey");
  });
});
