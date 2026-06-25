import { describe, it, expect } from "vitest";
import { inflationBand } from "./inflation";

describe("inflationBand — USA", () => {
  it("-0.1 -> deflation / bearish", () => {
    const r = inflationBand(-0.1, "USA");
    expect(r.band).toBe("deflation");
    expect(r.signal).toBe("bearish");
  });

  it("0.0 -> below / neutral (>=0, <1)", () => {
    const r = inflationBand(0.0, "USA");
    expect(r.band).toBe("below");
    expect(r.signal).toBe("neutral");
  });

  it("0.9 -> below / neutral", () => {
    const r = inflationBand(0.9, "USA");
    expect(r.band).toBe("below");
    expect(r.signal).toBe("neutral");
  });

  it("1.0 -> target / bullish (Grenze inklusiv)", () => {
    const r = inflationBand(1.0, "USA");
    expect(r.band).toBe("target");
    expect(r.signal).toBe("bullish");
  });

  it("3.0 -> target / bullish (Grenze inklusiv)", () => {
    const r = inflationBand(3.0, "USA");
    expect(r.band).toBe("target");
    expect(r.signal).toBe("bullish");
  });

  it("3.1 -> elevated / bearish", () => {
    const r = inflationBand(3.1, "USA");
    expect(r.band).toBe("elevated");
    expect(r.signal).toBe("bearish");
  });

  it("4.0 -> high / bearish", () => {
    const r = inflationBand(4.0, "USA");
    expect(r.band).toBe("high");
    expect(r.signal).toBe("bearish");
  });

  it("5.0 -> high / bearish", () => {
    const r = inflationBand(5.0, "USA");
    expect(r.band).toBe("high");
    expect(r.signal).toBe("bearish");
  });
});

describe("inflationBand — CH", () => {
  it("0.5 -> target (Grenze inklusiv)", () => {
    const r = inflationBand(0.5, "CH");
    expect(r.band).toBe("target");
    expect(r.signal).toBe("bullish");
  });

  it("2.0 -> target (Grenze inklusiv)", () => {
    const r = inflationBand(2.0, "CH");
    expect(r.band).toBe("target");
    expect(r.signal).toBe("bullish");
  });

  it("2.1 -> elevated / bearish", () => {
    const r = inflationBand(2.1, "CH");
    expect(r.band).toBe("elevated");
    expect(r.signal).toBe("bearish");
  });

  it("3.0 -> high / bearish", () => {
    const r = inflationBand(3.0, "CH");
    expect(r.band).toBe("high");
    expect(r.signal).toBe("bearish");
  });
});

describe("inflationBand — EUR (Eurozone, ECB-HICP-Aggregat ≠ Deutschland)", () => {
  // Die Eurozone nutzt dasselbe Band wie die USA (Ziel 1–3 %). Wichtig: Datenquelle ist
  // das ECB-HICP-Aggregat des Euroraums — KEIN einzelnes Land (insbesondere nicht Deutschland).
  it("2.4 -> target / bullish (EU-Band 1–3 %)", () => {
    const r = inflationBand(2.4, "EUR");
    expect(r.band).toBe("target");
    expect(r.signal).toBe("bullish");
  });

  it("4.0 -> high / bearish (EU-Band, >=4 %)", () => {
    const r = inflationBand(4.0, "EUR");
    expect(r.band).toBe("high");
    expect(r.signal).toBe("bearish");
  });
});

describe("inflationBand — null / UNAVAILABLE", () => {
  it("null -> unavailable, signal null, activeThreshold '—'", () => {
    const r = inflationBand(null, "USA");
    expect(r.band).toBe("unavailable");
    expect(r.signal).toBeNull();
    expect(r.activeThreshold).toBe("—");
  });
});

describe("inflationBand — activeThreshold", () => {
  it("USA elevated (3.1) -> enthaelt '3–4'", () => {
    const r = inflationBand(3.1, "USA");
    expect(r.activeThreshold).toContain("3");
    expect(r.activeThreshold).toContain("4");
  });

  it("CH target (1.0) -> enthaelt '0.5' und '2'", () => {
    const r = inflationBand(1.0, "CH");
    expect(r.activeThreshold).toContain("0.5");
    expect(r.activeThreshold).toContain("2");
  });
});
