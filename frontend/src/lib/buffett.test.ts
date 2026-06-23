import { describe, it, expect } from "vitest";
import { sortRows, filterRows, vsMedianLabel } from "./buffett";
import type { BuffettCountry } from "../contract/cockpit";

const makeCountry = (overrides: Partial<BuffettCountry>): BuffettCountry => ({
  iso3: "TST", name: "Test", ratioPct: 100, signal: "neutral",
  zScore: 0, year: 2024, history: [],
  ...overrides,
});

const rows: BuffettCountry[] = [
  makeCountry({ iso3: "USA", name: "USA",         ratioPct: 198, signal: "bearish", zScore: +2.1 }),
  makeCountry({ iso3: "CHE", name: "Schweiz",     ratioPct: 211, signal: "bearish", zScore: +0.6 }),
  makeCountry({ iso3: "DEU", name: "Deutschland", ratioPct: 55,  signal: "bullish", zScore: -0.9 }),
  makeCountry({ iso3: "JPN", name: "Japan",       ratioPct: 145, signal: "bearish", zScore: +1.6 }),
  makeCountry({ iso3: "GBR", name: "UK",          ratioPct: 100, signal: "neutral", zScore: -0.2 }),
];

describe("sortRows — ratioPct desc", () => {
  it("hoechste ratio zuerst", () => {
    const sorted = sortRows(rows, "ratioPct", "desc");
    expect(sorted[0].ratioPct).toBe(211);
    expect(sorted[1].ratioPct).toBe(198);
    expect(sorted[sorted.length - 1].ratioPct).toBe(55);
  });

  it("ratioPct asc: niedrigste zuerst", () => {
    const sorted = sortRows(rows, "ratioPct", "asc");
    expect(sorted[0].ratioPct).toBe(55);
  });
});

describe("sortRows — name", () => {
  it("alphabetisch asc", () => {
    const sorted = sortRows(rows, "name", "asc");
    expect(sorted[0].name).toBe("Deutschland");
    expect(sorted[sorted.length - 1].name).toBe("USA");
  });
});

describe("sortRows — zScore mit null ans Ende", () => {
  const rowsWithNull = [
    ...rows,
    makeCountry({ iso3: "NUL", name: "Null", ratioPct: 80, signal: null, zScore: null }),
  ];

  it("null-Land ganz hinten bei asc", () => {
    const sorted = sortRows(rowsWithNull, "zScore", "asc");
    expect(sorted[sorted.length - 1].zScore).toBeNull();
  });

  it("null-Land ganz hinten bei desc", () => {
    const sorted = sortRows(rowsWithNull, "zScore", "desc");
    expect(sorted[sorted.length - 1].zScore).toBeNull();
  });
});

describe("filterRows — onlyZOutlier", () => {
  it("|Z|>=1.5 (z=+1.6) wird behalten", () => {
    const filtered = filterRows(rows, { onlyZOutlier: true, onlyBearish: false });
    const isos = filtered.map((r) => r.iso3);
    expect(isos).toContain("JPN"); // zScore +1.6
  });

  it("|Z|=1.5 (Grenze) wird behalten", () => {
    const r = [makeCountry({ iso3: "BND", name: "Grenze", zScore: 1.5, signal: "bearish" })];
    const filtered = filterRows(r, { onlyZOutlier: true, onlyBearish: false });
    expect(filtered).toHaveLength(1);
  });

  it("|Z|=+2.1 (Anomalie) wird behalten", () => {
    const filtered = filterRows(rows, { onlyZOutlier: true, onlyBearish: false });
    const isos = filtered.map((r) => r.iso3);
    expect(isos).toContain("USA"); // zScore +2.1
  });

  it("|Z|=+0.6 -> nicht behalten (< 1.5)", () => {
    const filtered = filterRows(rows, { onlyZOutlier: true, onlyBearish: false });
    const isos = filtered.map((r) => r.iso3);
    expect(isos).not.toContain("CHE"); // zScore +0.6
  });

  it("zScore=null -> nicht behalten", () => {
    const r = [makeCountry({ iso3: "NUL", name: "Null", zScore: null, signal: "bearish" })];
    const filtered = filterRows(r, { onlyZOutlier: true, onlyBearish: false });
    expect(filtered).toHaveLength(0);
  });
});

describe("filterRows — onlyBearish", () => {
  it("nur signal===bearish", () => {
    const filtered = filterRows(rows, { onlyZOutlier: false, onlyBearish: true });
    expect(filtered.every((r) => r.signal === "bearish")).toBe(true);
    expect(filtered.length).toBeGreaterThan(0);
  });
});

describe("filterRows — beide Filter (Schnittmenge)", () => {
  it("onlyZOutlier + onlyBearish: nur bearish mit |Z|>=1.5", () => {
    const filtered = filterRows(rows, { onlyZOutlier: true, onlyBearish: true });
    // USA (bearish, +2.1) und JPN (bearish, +1.6) sollen drin sein
    const isos = filtered.map((r) => r.iso3);
    expect(isos).toContain("USA");
    expect(isos).toContain("JPN");
    // CHE (+0.6) sollte raus
    expect(isos).not.toContain("CHE");
    // DEU (bullish) sollte raus
    expect(isos).not.toContain("DEU");
  });
});

describe("vsMedianLabel", () => {
  it("198/92 ~ 2.15 -> 'deutlich >'", () => {
    const r = vsMedianLabel(198, 92);
    expect(r.label).toBe("deutlich >");
    expect(r.ratio).toBeCloseTo(198 / 92, 5);
  });

  it("55/92 ~ 0.598 -> 'deutlich <' (< 0.67)", () => {
    const r = vsMedianLabel(55, 92);
    expect(r.label).toBe("deutlich <");
  });

  it("92/92 = 1.0 -> '<' (ratio 1.0 Grenze, nicht >1.0)", () => {
    const r = vsMedianLabel(92, 92);
    expect(r.label).toBe("<");
    expect(r.ratio).toBe(1.0);
  });

  it("median <= 0 -> label '—', ratio 0 (defensiv)", () => {
    const r = vsMedianLabel(100, 0);
    expect(r.label).toBe("—");
    expect(r.ratio).toBe(0);
  });

  it("120/92 ~ 1.30 -> '>' (>1.0 aber <1.5)", () => {
    const r = vsMedianLabel(120, 92);
    expect(r.label).toBe(">");
  });
});
