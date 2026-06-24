import { describe, it, expect } from "vitest";
import { sortRows, filterRows, vsMedianLabel, toMapPoints, ISO3_TO_MAP_NAME } from "./buffett";
import { demoBuffett } from "../data/demo/cockpit";
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

  it("92/92 = 1.0 -> '≈ am Median' (ratio in [0.95, 1.05])", () => {
    const r = vsMedianLabel(92, 92);
    expect(r.label).toBe("≈ am Median");
    expect(r.ratio).toBe(1.0);
  });

  it("median <= 0 -> label '—', ratio 0 (defensiv)", () => {
    const r = vsMedianLabel(100, 0);
    expect(r.label).toBe("—");
    expect(r.ratio).toBe(0);
  });

  it("120/92 ~ 1.30 -> '>' (>1.05 aber <1.5)", () => {
    const r = vsMedianLabel(120, 92);
    expect(r.label).toBe(">");
  });

  it("100/92 ~ 1.087 -> '>' (ratio > 1.05)", () => {
    const r = vsMedianLabel(100, 92);
    expect(r.label).toBe(">");
    expect(r.ratio).toBeCloseTo(100 / 92, 5);
  });

  it("80/92 ~ 0.87 -> '<' (0.67 <= ratio < 0.95)", () => {
    const r = vsMedianLabel(80, 92);
    expect(r.label).toBe("<");
    expect(r.ratio).toBeCloseTo(80 / 92, 5);
  });

  it("50/0 -> label '—', ratio 0 (median <= 0)", () => {
    const r = vsMedianLabel(50, 0);
    expect(r.label).toBe("—");
    expect(r.ratio).toBe(0);
  });
});

// ---- toMapPoints: iso3 -> englischer GeoJSON-Name ----
// GeoJSON (world.geo.json) traegt nur englische Namen; Demo-Daten haben deutsche Namen.
// toMapPoints mappt per iso3 auf den passenden GeoJSON-Namen damit die Choropleth-Karte
// die Laender findet (kein Match -> graue Karte).
const makeC = (overrides: Partial<BuffettCountry>): BuffettCountry => ({
  iso3: "TST", name: "Test", ratioPct: 100, signal: "neutral",
  zScore: 0, year: 2024, history: [],
  ...overrides,
});

describe("toMapPoints — iso3 auf GeoJSON-Namen mappen", () => {
  it("USA -> 'United States'", () => {
    const pts = toMapPoints([makeC({ iso3: "USA", name: "USA", ratioPct: 198, signal: "bearish" })]);
    expect(pts[0].name).toBe("United States");
  });

  it("CHE -> 'Switzerland'", () => {
    const pts = toMapPoints([makeC({ iso3: "CHE", name: "Schweiz", ratioPct: 211, signal: "bearish" })]);
    expect(pts[0].name).toBe("Switzerland");
  });

  it("DEU -> 'Germany'", () => {
    const pts = toMapPoints([makeC({ iso3: "DEU", name: "Deutschland", ratioPct: 55, signal: "bullish" })]);
    expect(pts[0].name).toBe("Germany");
  });

  it("JPN -> 'Japan'", () => {
    const pts = toMapPoints([makeC({ iso3: "JPN", name: "Japan", ratioPct: 145, signal: "bearish" })]);
    expect(pts[0].name).toBe("Japan");
  });

  it("GBR -> 'United Kingdom'", () => {
    const pts = toMapPoints([makeC({ iso3: "GBR", name: "UK", ratioPct: 100, signal: "neutral" })]);
    expect(pts[0].name).toBe("United Kingdom");
  });

  it("unbekanntes iso3 -> Fallback auf deutschen name", () => {
    const pts = toMapPoints([makeC({ iso3: "XYZ", name: "Unbekannt", ratioPct: 80, signal: "neutral" })]);
    expect(pts[0].name).toBe("Unbekannt");
  });

  it("value === ratioPct", () => {
    const pts = toMapPoints([makeC({ iso3: "USA", name: "USA", ratioPct: 198, signal: "bearish" })]);
    expect(pts[0].value).toBe(198);
  });

  it("signal wird durchgereicht", () => {
    const pts = toMapPoints([makeC({ iso3: "DEU", name: "Deutschland", ratioPct: 55, signal: "bullish" })]);
    expect(pts[0].signal).toBe("bullish");
  });

  it("iso3 wird durchgereicht", () => {
    const pts = toMapPoints([makeC({ iso3: "USA", name: "USA", ratioPct: 198, signal: "bearish" })]);
    expect(pts[0].iso3).toBe("USA");
  });

  it("mehrere Laender korrekt gemappt", () => {
    const countries = [
      makeC({ iso3: "USA", name: "USA",         ratioPct: 198, signal: "bearish" }),
      makeC({ iso3: "CHE", name: "Schweiz",     ratioPct: 211, signal: "bearish" }),
      makeC({ iso3: "DEU", name: "Deutschland", ratioPct: 55,  signal: "bullish" }),
    ];
    const pts = toMapPoints(countries);
    expect(pts[0].name).toBe("United States");
    expect(pts[1].name).toBe("Switzerland");
    expect(pts[2].name).toBe("Germany");
  });
});

// Guard (Befund #1, PR #44-Review): JEDES Land aus den Demo-Daten MUSS in ISO3_TO_MAP_NAME stehen.
// Sonst faellt toMapPoints auf den deutschen Namen zurueck -> kein GeoJSON-Match -> stumm graue
// Karte. Dieser Test schlaegt laut fehl, sobald ein Demo-Land ohne Mapping hinzukommt — und
// erinnert beim Echt-Anschluss (fetchBuffett), die Tabelle auf alle Laender zu erweitern.
describe("ISO3_TO_MAP_NAME — Vollstaendigkeit ggü. Demo-Daten", () => {
  it("jedes Demo-Buffett-Land ist gemappt (kein stiller Fallback)", () => {
    const unmapped = demoBuffett().countries
      .map((c) => c.iso3)
      .filter((iso3) => !(iso3 in ISO3_TO_MAP_NAME));
    expect(unmapped).toEqual([]);
  });

  it("toMapPoints liefert fuer Demo-Daten keinen deutschen Fallback-Namen", () => {
    const points = toMapPoints(demoBuffett().countries);
    // Alle gemappten Namen sind die englischen GeoJSON-Namen -> in den Werten der Tabelle.
    const mappedValues = Object.values(ISO3_TO_MAP_NAME);
    expect(points.every((p) => mappedValues.includes(p.name))).toBe(true);
  });
});
