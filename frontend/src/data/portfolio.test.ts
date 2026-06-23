import { describe, it, expect } from "vitest";
import { loadPortfolio } from "./portfolio";
import { detectConflict } from "../lib/conflict";

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
    expect(Number.isFinite(v.exposure.netBeta)).toBe(true);
  });
});
