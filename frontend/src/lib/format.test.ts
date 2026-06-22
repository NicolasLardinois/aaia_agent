import { describe, it, expect } from "vitest";
import { formatConfidence } from "./format";

describe("formatConfidence", () => {
  it("rundet auf ganze Prozent mit Leerzeichen", () => {
    expect(formatConfidence(0.71)).toBe("71 %");
  });
  it("behandelt 0 und 1", () => {
    expect(formatConfidence(0)).toBe("0 %");
    expect(formatConfidence(1)).toBe("100 %");
  });
  it("clamped Werte außerhalb [0,1]", () => {
    expect(formatConfidence(-0.2)).toBe("0 %");
    expect(formatConfidence(1.5)).toBe("100 %");
  });
});
