import { describe, it, expect } from "vitest";
import { grossExposure, netExposure, netBeta } from "./exposure";
import type { PositionDTO } from "../contract/portfolio";

// minimaler Positions-Bauer (nur Felder, die die Exposure-Mathematik liest)
function p(partial: Partial<PositionDTO>): PositionDTO {
  return {
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 10, entryPrice: 100, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 },
    ...partial,
  };
}

describe("grossExposure (Σ|Position|)", () => {
  it("leeres Portfolio => 0", () => {
    expect(grossExposure([])).toBe(0);
  });
  it("addiert Betraege unabhaengig von der Richtung", () => {
    expect(grossExposure([p({ sizePctNav: 12, direction: "long" }), p({ sizePctNav: 5, direction: "short" })])).toBe(17);
  });
});

describe("netExposure (long − short)", () => {
  it("nur long => Summe der long-Groessen", () => {
    expect(netExposure([p({ sizePctNav: 12 }), p({ sizePctNav: 9 })])).toBe(21);
  });
  it("nur short => negativ", () => {
    expect(netExposure([p({ sizePctNav: 5, direction: "short" })])).toBe(-5);
  });
  it("gemischt => long minus short", () => {
    expect(netExposure([p({ sizePctNav: 12, direction: "long" }), p({ sizePctNav: 5, direction: "short" })])).toBe(7);
  });
});

describe("netBeta (aktien-only, signiert × β)", () => {
  it("ohne Aktien (nur Bond/Commodity/Precious) => null (UNAVAILABLE, NICHT 0)", () => {
    // Kein einziger Aktien-Beta-Wert vorhanden -> net_beta ist UNBEKANNT, nicht 0.
    // 0 wuerde faelschlich "marktneutral" suggerieren (AGENTS.md §3: UNAVAILABLE ≠ 0).
    expect(netBeta([
      p({ underlying: "bond", beta: null }),
      p({ underlying: "commodity", beta: null }),
      p({ underlying: "precious_metal", beta: null }),
    ])).toBeNull();
  });
  it("leeres Portfolio => null (kein net_beta bildbar)", () => {
    expect(netBeta([])).toBeNull();
  });
  it("Aktien vorhanden, aber ALLE beta=null => null (UNAVAILABLE, nicht 0)", () => {
    // Beta-Feed komplett ausgefallen -> net_beta unbekannt, nie als 0 ausgewiesen.
    expect(netBeta([
      p({ underlying: "equity", direction: "long", sizePctNav: 10, beta: null }),
      p({ underlying: "equity_index", direction: "short", sizePctNav: 5, beta: null }),
    ])).toBeNull();
  });
  it("zaehlt equity und equity_index, nicht bond/commodity/precious", () => {
    // long 10 (β1.2) + short 5 (β1.0) aktien; bond 20 ignoriert
    // = 10*1.2 − 5*1.0 = 12 − 5 = 7
    expect(netBeta([
      p({ underlying: "equity", direction: "long", sizePctNav: 10, beta: 1.2 }),
      p({ underlying: "equity_index", direction: "short", sizePctNav: 5, beta: 1.0 }),
      p({ underlying: "bond", direction: "long", sizePctNav: 20, beta: null }),
    ])).toBeCloseTo(7, 6);
  });
  it("Aktie mit beta=null wird NICHT mitgezaehlt (UNAVAILABLE, nie als 0/1 unterstellt)", () => {
    // nur die erste Aktie zaehlt: 10*1.5 = 15; die zweite (beta null) faellt raus
    expect(netBeta([
      p({ underlying: "equity", direction: "long", sizePctNav: 10, beta: 1.5 }),
      p({ underlying: "equity", direction: "long", sizePctNav: 8, beta: null }),
    ])).toBeCloseTo(15, 6);
  });
});
