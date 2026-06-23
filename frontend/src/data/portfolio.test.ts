import { describe, it, expect } from "vitest";
import { loadPortfolio } from "./portfolio";
import { detectConflict } from "../lib/conflict";
import { detectKlumpen } from "../lib/klumpen";
import { demoPortfolio } from "./demo/portfolio";

describe("loadPortfolio (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit Positionen, Exposure, Klumpen, Hedges", async () => {
    const v = await loadPortfolio();
    expect(v.isDemo).toBe(true);
    expect(v.positions.length).toBeGreaterThanOrEqual(4);
    expect(v.exposure.grossPct).toBeGreaterThan(0);
    expect(v.klumpen.length).toBeGreaterThanOrEqual(1);   // mind. eine Klumpen-Warnung (Tech)
    expect(v.hedges.length).toBeGreaterThanOrEqual(1);    // mind. ein Hedge-Vorschlag
  });
  it("enthaelt mindestens einen Konflikt-Fall (long gehalten, Urteil SELL)", async () => {
    const v = await loadPortfolio();
    const conflicts = v.positions.filter((p) => detectConflict(p.direction, p.judgment));
    expect(conflicts.some((p) => p.ticker === "XLE")).toBe(true);
  });
  it("net_beta zaehlt nur Aktien/Index (Bonds/Edelmetalle ausgenommen)", async () => {
    const v = await loadPortfolio();
    // Gold-Future (beta null) + TLT (bond) duerfen das net_beta nicht beeinflussen.
    // Demo-Positionen: AAPL (12×1.25) + MSFT (15×1.10) − TSLA (5×1.80) + XLE (9×1.05) = 31.95
    expect(v.exposure.netBeta).toBeCloseTo(31.95, 1);
  });
});

describe("Demo-Portfolio Klumpen: zwei bewusste Ueberschreitungen", () => {
  it("Technologie-Sektor: 47 % > 25 % Limit (27 NAV = share/gross = 27/57)", () => {
    const demo = demoPortfolio();
    const techKlumpen = demo.klumpen.find((k) => k.dimension === "sector" && k.name === "Technologie");
    expect(techKlumpen).toBeDefined();
    expect(techKlumpen?.pct).toBeCloseTo(27 / 57, 2);  // ca. 0.474 = 47 %
    expect(techKlumpen?.pct).toBeGreaterThan(demo.limits.sector);
  });
  it("USA-Geographie: 72 % > 70 % Limit (41 NAV = share/gross = 41/57)", () => {
    const demo = demoPortfolio();
    const usaKlumpen = demo.klumpen.find((k) => k.dimension === "geography" && k.name === "USA");
    expect(usaKlumpen).toBeDefined();
    expect(usaKlumpen?.pct).toBeCloseTo(41 / 57, 2);  // ca. 0.719 = 72 %
    expect(usaKlumpen?.pct).toBeGreaterThan(demo.limits.geography);
  });
});
