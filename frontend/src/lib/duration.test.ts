import { describe, it, expect } from "vitest";
import { durationRisk } from "./duration";

describe("durationRisk", () => {
  it("null => unbekannt (UNAVAILABLE, nie 0)", () => {
    expect(durationRisk(null).level).toBe("unbekannt");
  });
  it("< 3 Jahre => niedrig", () => {
    expect(durationRisk(2.5).level).toBe("niedrig");
  });
  it("genau 3 => mittel (Grenze gehoert ins mittlere Band)", () => {
    expect(durationRisk(3).level).toBe("mittel");
  });
  it("3..7 => mittel", () => {
    expect(durationRisk(6).level).toBe("mittel");
  });
  it("genau 7 => hoch (Grenze gehoert ins hohe Band)", () => {
    expect(durationRisk(7).level).toBe("hoch");
  });
  it("> 7 => hoch", () => {
    expect(durationRisk(12).level).toBe("hoch");
  });
});
