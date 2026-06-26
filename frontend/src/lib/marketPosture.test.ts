import { describe, it, expect } from "vitest";
import { marketPosture, postureLabel } from "./marketPosture";
import type { Domain } from "./contract";

// Hilfsfunktion: baut eine Domain mit Signal/Status.
function dom(signal: Domain["signal"], status: Domain["status"] = "available"): Domain {
  return { key: "commodities", signal, status };
}

describe("marketPosture", () => {
  it("zaehlt die Signale der verfuegbaren Domaenen", () => {
    const p = marketPosture([dom("bullish"), dom("bullish"), dom("bearish"), dom("neutral")]);
    expect(p.bullish).toBe(2);
    expect(p.bearish).toBe(1);
    expect(p.neutral).toBe(1);
    expect(p.unavailable).toBe(0);
    expect(p.available).toBe(4);
  });

  it("zaehlt unavailable und signal=null als 'ohne Daten', nicht als neutral", () => {
    const p = marketPosture([dom(null, "unavailable"), dom("neutral"), dom(null)]);
    expect(p.unavailable).toBe(2);
    expect(p.neutral).toBe(1);
    expect(p.available).toBe(1);
  });

  it("Tendenz = risk-on, wenn bullish > bearish", () => {
    expect(marketPosture([dom("bullish"), dom("bullish"), dom("bearish")]).tone).toBe("risk-on");
  });

  it("Tendenz = risk-off, wenn bearish > bullish", () => {
    expect(marketPosture([dom("bearish"), dom("bearish"), dom("bullish")]).tone).toBe("risk-off");
  });

  it("Tendenz = mixed bei Gleichstand bullish/bearish", () => {
    expect(marketPosture([dom("bullish"), dom("bearish"), dom("neutral")]).tone).toBe("mixed");
  });

  it("Tendenz = mixed, wenn nur neutrale Signale vorliegen", () => {
    expect(marketPosture([dom("neutral"), dom("neutral")]).tone).toBe("mixed");
  });

  it("Tendenz = unknown, wenn keine Domaene Daten hat", () => {
    const p = marketPosture([dom(null, "unavailable"), dom(null, "unavailable")]);
    expect(p.tone).toBe("unknown");
    expect(p.available).toBe(0);
  });

  it("leere Liste -> unknown, alle Zaehler 0", () => {
    const p = marketPosture([]);
    expect(p).toEqual({ bullish: 0, bearish: 0, neutral: 0, unavailable: 0, available: 0, tone: "unknown" });
  });
});

describe("postureLabel", () => {
  it("uebersetzt jede Tendenz in einen deutschen Klartext", () => {
    expect(postureLabel("risk-on")).toMatch(/risiko/i);
    expect(postureLabel("risk-off")).toMatch(/defensiv|vorsicht/i);
    expect(postureLabel("mixed")).toMatch(/gemischt/i);
    expect(postureLabel("unknown")).toMatch(/keine|daten/i);
  });
});
