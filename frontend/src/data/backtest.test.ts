// frontend/src/data/backtest.test.ts
import { describe, it, expect } from "vitest";
import { loadBacktest } from "./backtest";
import { hitRate, filterResults } from "../lib/backtest";

describe("loadBacktest (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit Roh-Ergebnissen", async () => {
    const v = await loadBacktest();
    expect(v.isDemo).toBe(true);
    expect(v.results.length).toBeGreaterThanOrEqual(12);
  });
  it("deckt alle drei Bereiche ab (top_down/bottom_up/judgment)", async () => {
    const v = await loadBacktest();
    for (const area of ["top_down", "bottom_up", "judgment"] as const) {
      expect(v.results.some((r) => r.area === area)).toBe(true);
    }
  });
  it("Bereichs-Aggregate sind konsistent zu hitRate ueber die Roh-Ergebnisse (eine Quelle der Wahrheit)", async () => {
    const v = await loadBacktest();
    for (const a of v.areas) {
      const hr = hitRate(filterResults(v.results, { area: a.area }));
      expect(a.sampleSize).toBe(hr.n);
      expect(a.hitRatePct).toBe(hr.rate);
    }
  });
  it("bietet die Filter-Achsen Ticker/underlying/Regime/Horizont an (US32)", async () => {
    const v = await loadBacktest();
    const tickers = new Set(v.results.map((r) => r.ticker));
    const underlyings = new Set(v.results.map((r) => r.underlying));
    const regimes = new Set(v.results.map((r) => r.regime));
    const horizons = new Set(v.results.map((r) => r.horizon));
    expect(tickers.size).toBeGreaterThanOrEqual(2);
    expect(underlyings.size).toBeGreaterThanOrEqual(2);
    expect(regimes.size).toBeGreaterThanOrEqual(2);
    expect(horizons.size).toBeGreaterThanOrEqual(2);
  });
  it("zeigt mindestens eine ausgefallene Quelle (UNAVAILABLE-Pfad, Spec §5.4)", async () => {
    const v = await loadBacktest();
    expect(v.sourcesActive).toBeLessThan(v.sourcesTotal);
    expect(v.failed.length).toBeGreaterThanOrEqual(1);
  });
});
