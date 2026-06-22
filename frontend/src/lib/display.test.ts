import { describe, it, expect } from "vitest";
import { signalToVisual, isUnavailable, sourcesLabel } from "./display";
import type { Domain } from "./contract";

describe("signalToVisual", () => {
  it("mappt Signale auf Wort + Farbe", () => {
    expect(signalToVisual("bullish")).toEqual({ label: "BULLISH", colorClass: "text-green-600" });
    expect(signalToVisual("bearish")).toEqual({ label: "BEARISH", colorClass: "text-red-600" });
    expect(signalToVisual("neutral")).toEqual({ label: "NEUTRAL", colorClass: "text-slate-500" });
  });
  it("zeigt null als 'nicht verfuegbar' (kein neutrales Signal)", () => {
    expect(signalToVisual(null)).toEqual({ label: "nicht verfügbar", colorClass: "text-slate-400" });
  });
});

describe("isUnavailable", () => {
  const base: Domain = { key: "sentiment", signal: "bearish", status: "available" };
  it("false bei verfuegbarer Domaene", () => {
    expect(isUnavailable(base)).toBe(false);
  });
  it("true bei status unavailable", () => {
    expect(isUnavailable({ ...base, status: "unavailable", signal: null })).toBe(true);
  });
  it("true wenn signal null ist (auch ohne status-Flag)", () => {
    expect(isUnavailable({ ...base, signal: null })).toBe(true);
  });
});

describe("sourcesLabel", () => {
  it("formatiert x/y Quellen aktiv", () => {
    expect(sourcesLabel(4, 5)).toBe("4/5 Quellen aktiv");
    expect(sourcesLabel(0, 5)).toBe("0/5 Quellen aktiv");
  });
});
