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
});
