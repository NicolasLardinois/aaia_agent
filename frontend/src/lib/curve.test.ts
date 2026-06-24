import { describe, it, expect } from "vitest";
import { yieldSpreadStatus } from "./curve";

describe("yieldSpreadStatus", () => {
  it("negativer Spread = invertiert (Rezessions-FrUehsignal)", () => {
    expect(yieldSpreadStatus(-0.2)).toEqual({ value: -0.2, inverted: true });
  });
  it("positiver/Null-Spread = nicht invertiert", () => {
    expect(yieldSpreadStatus(0.4)).toEqual({ value: 0.4, inverted: false });
    expect(yieldSpreadStatus(0)).toEqual({ value: 0, inverted: false });
  });
});
