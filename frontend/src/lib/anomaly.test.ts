import { describe, it, expect } from "vitest";
import { zScoreFlag, anomalySeverityToVisual } from "./anomaly";

describe("zScoreFlag", () => {
  it("|z|>2.0 => anomaly, |z|>=1.5 => watch, sonst none", () => {
    expect(zScoreFlag(2.1)).toBe("anomaly");
    expect(zScoreFlag(-2.1)).toBe("anomaly");
    expect(zScoreFlag(1.5)).toBe("watch");
    expect(zScoreFlag(-1.6)).toBe("watch");
    expect(zScoreFlag(0.9)).toBe("none");
  });
});

describe("anomalySeverityToVisual", () => {
  it("Schwere -> Label + Farbe", () => {
    expect(anomalySeverityToVisual("high").colorClass).toContain("red");
    expect(anomalySeverityToVisual("none").colorClass).toContain("slate");
  });
});
