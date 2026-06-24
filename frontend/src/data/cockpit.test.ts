import { describe, it, expect } from "vitest";
import {
  loadMacro, loadCommodities, loadSentiment,
  loadYieldCurve, loadSectors, loadBuffett, loadBigMac,
} from "./cockpit";

describe("Tausch-Naht — isDemo + SourceHealthMeta", () => {
  it("loadMacro: isDemo true, failed.length === sourcesTotal - sourcesActive", async () => {
    const v = await loadMacro();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadCommodities: isDemo true, failed konsistent", async () => {
    const v = await loadCommodities();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadSentiment: isDemo true, failed konsistent", async () => {
    const v = await loadSentiment();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadYieldCurve: isDemo true, failed konsistent", async () => {
    const v = await loadYieldCurve();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadSectors: isDemo true, failed konsistent", async () => {
    const v = await loadSectors();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadBuffett: isDemo true, failed konsistent", async () => {
    const v = await loadBuffett();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });

  it("loadBigMac: isDemo true, failed konsistent", async () => {
    const v = await loadBigMac();
    expect(v.isDemo).toBe(true);
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
  });
});

describe("loadSectors — UNAVAILABLE-Pfad", () => {
  it("enthaelt genau einen sector mit signal === null", async () => {
    const v = await loadSectors();
    const nullSignals = v.sectors.filter((s) => s.signal === null);
    expect(nullSignals).toHaveLength(1);
  });
});

describe("loadMacro — Regionen", () => {
  it("hat 3 Regionen USA/DE/CH — KEIN EU-Eintrag", async () => {
    const v = await loadMacro();
    const regions = v.inflation.map((r) => r.region);
    expect(regions).toContain("USA");
    expect(regions).toContain("DE");
    expect(regions).toContain("CH");
    expect(regions).not.toContain("EU");
    expect(v.inflation).toHaveLength(3);
  });
});

describe("loadYieldCurve — Spreads", () => {
  it("hat genau 3 Spreads mit den erwarteten Paaren", async () => {
    const v = await loadYieldCurve();
    const pairs = v.spreads.map((s) => s.pair);
    expect(pairs).toContain("10J-2J");
    expect(pairs).toContain("10J-3M");
    expect(pairs).toContain("30J-10J");
    expect(v.spreads).toHaveLength(3);
  });
});

describe("loadBuffett — Konsistenz", () => {
  it("analyzedIso3 ist in countries vorhanden; globalMedian > 0", async () => {
    const v = await loadBuffett();
    const isos = v.countries.map((c) => c.iso3);
    expect(isos).toContain(v.analyzedIso3);
    expect(v.globalMedian).toBeGreaterThan(0);
  });
});
