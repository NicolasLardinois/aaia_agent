import { describe, it, expect } from "vitest";
import { confidenceFlags, consistencyHint, verdictToVisual } from "./judgment";

describe("confidenceFlags", () => {
  it("auto-HOLD ab unter 0.50, Cash-Bias ab unter 0.35 (Konzept/frontend_notes)", () => {
    expect(confidenceFlags(0.60)).toEqual({ autoHold: false, cashBias: false });
    expect(confidenceFlags(0.50)).toEqual({ autoHold: false, cashBias: false }); // genau auf Schwelle: nicht ausgeloest
    expect(confidenceFlags(0.49)).toEqual({ autoHold: true, cashBias: false });
    expect(confidenceFlags(0.35)).toEqual({ autoHold: true, cashBias: false }); // genau auf Schwelle
    expect(confidenceFlags(0.34)).toEqual({ autoHold: true, cashBias: true });
  });
});

describe("consistencyHint", () => {
  it("beide bearish -> starkes bearishes Gesamtbild", () => {
    expect(consistencyHint("SELL", "SHORT")).toMatch(/bearish/i);
  });
  it("beide schwach/NONE -> kein Edge", () => {
    expect(consistencyHint("NONE", "NONE")).toMatch(/kein Edge/i);
  });
  it("gemischt -> kein Hinweis", () => {
    expect(consistencyHint("BUY", "NONE")).toBeNull();
  });
});

describe("verdictToVisual", () => {
  it("BUY/COVER bull, SELL/SHORT bear, HOLD neutral, NONE muted (Design-Tokens)", () => {
    // Finanzsemantik auf Tokens: bullish->bull, bearish->bear, HOLD ohne Richtung->neutral,
    // NONE = keine Position/nicht anwendbar -> muted (kein Signal, wie UNAVAILABLE).
    expect(verdictToVisual("BUY").colorClass).toBe("text-bull");
    expect(verdictToVisual("COVER").colorClass).toBe("text-bull");
    expect(verdictToVisual("SELL").colorClass).toBe("text-bear");
    expect(verdictToVisual("SHORT").colorClass).toBe("text-bear");
    expect(verdictToVisual("HOLD").colorClass).toBe("text-neutral");
    expect(verdictToVisual("NONE").colorClass).toBe("text-muted");
  });
});
