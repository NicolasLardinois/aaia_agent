import { describe, it, expect } from "vitest";
import { loadDeepDive } from "./deepdive";

describe("loadDeepDive (Tausch-Naht)", () => {
  it("liefert fuer bekannten Ticker einen Demo-View (isDemo:true, found:true)", async () => {
    const v = await loadDeepDive("AAPL");
    expect(v.isDemo).toBe(true);
    expect(v.found).toBe(true);
    expect(v.ticker).toBe("AAPL");
    expect(v.underlying).toBe("equity");
  });
  it("liefert fuer GC=F den Futures-Block + wrapper=future", async () => {
    const v = await loadDeepDive("GC=F");
    expect(v.wrapper).toBe("future");
    expect(v.futures).toBeTruthy();
  });
  it("liefert fuer unbekannten Ticker eine nicht-gefunden-Ansicht (found:false)", async () => {
    const v = await loadDeepDive("ZZZZ");
    expect(v.found).toBe(false);
  });
  it("AAPL: failed-Zaehler-Invariante (failed.length === sourcesTotal - sourcesActive)", async () => {
    const v = await loadDeepDive("AAPL");
    expect(v.failed.length).toBe(v.sourcesTotal - v.sourcesActive);
    // AAPL: sourcesTotal=6, sourcesActive=5, failed.length=1 (Earnings-Trend Stub)
    expect(v.sourcesTotal).toBe(6);
    expect(v.sourcesActive).toBe(5);
    expect(v.failed.length).toBe(1);
  });
});
