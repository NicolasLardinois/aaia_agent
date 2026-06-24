// frontend/src/lib/backtest.test.ts
import { describe, it, expect } from "vitest";
import { filterResults, hitRate, equityCurve, formatHitRate } from "./backtest";
import type { BacktestResult } from "../contract/backtest";

// Kleines, kontrolliertes Set: 4 Ergebnisse quer ueber Bereich/Ticker/underlying/Regime/Horizont.
const R: BacktestResult[] = [
  { id: "1", area: "top_down",  ticker: "SPY",  underlying: "equity_index",   regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-01-01" },
  { id: "2", area: "top_down",  ticker: "SPY",  underlying: "equity_index",   regime: "ABSCHWUNG",  horizon: 60, correct: false, timestamp: "2026-02-01" },
  { id: "3", area: "judgment",  ticker: "AAPL", underlying: "equity",         regime: "AUFSCHWUNG", horizon: 90, correct: true,  timestamp: "2026-03-01" },
  { id: "4", area: "bottom_up", ticker: "GC=F", underlying: "precious_metal", regime: "AUFSCHWUNG", horizon: 30, correct: true,  timestamp: "2026-04-01" },
];

describe("filterResults (US32 — additiv/UND)", () => {
  it("ohne Filter => unveraendert", () => {
    expect(filterResults(R, {})).toHaveLength(4);
  });
  it("nach Ticker", () => {
    expect(filterResults(R, { ticker: "SPY" })).toHaveLength(2);
  });
  it("nach underlying (Asset-Klasse)", () => {
    expect(filterResults(R, { underlying: "equity" }).map((r) => r.id)).toEqual(["3"]);
  });
  it("nach Regime", () => {
    expect(filterResults(R, { regime: "AUFSCHWUNG" })).toHaveLength(3);
  });
  it("nach Horizont (Zeitfenster)", () => {
    expect(filterResults(R, { horizon: 30 })).toHaveLength(2);
  });
  it("kombiniert (UND): Bereich + Regime", () => {
    expect(filterResults(R, { area: "top_down", regime: "AUFSCHWUNG" }).map((r) => r.id)).toEqual(["1"]);
  });
  it("Filter ohne Treffer => leere Menge", () => {
    expect(filterResults(R, { ticker: "TSLA" })).toEqual([]);
  });
});

describe("hitRate (US31 — Trefferquote + n; UNAVAILABLE != 0)", () => {
  it("leere Menge => rate:null, n:0 (n.v., NICHT 0 %)", () => {
    expect(hitRate([])).toEqual({ rate: null, n: 0 });
  });
  it("ein einziger korrekter Treffer => 100 %, n:1", () => {
    expect(hitRate([R[0]])).toEqual({ rate: 100, n: 1 });
  });
  it("ein einziger falscher Treffer => 0 % (legitim bei n>0), n:1", () => {
    expect(hitRate([R[1]])).toEqual({ rate: 0, n: 1 });
  });
  it("3 von 4 korrekt => 75 %, n:4", () => {
    const hr = hitRate(R);
    expect(hr.n).toBe(4);
    expect(hr.rate).toBeCloseTo(75, 5);
  });
});

describe("equityCurve (US31 — kumulierte Trefferquote ueber die Zeit)", () => {
  it("leere Menge => leeres Array (keine Null-Linie)", () => {
    expect(equityCurve([])).toEqual([]);
  });
  it("ein Punkt je Ergebnis, chronologisch sortiert", () => {
    const pts = equityCurve(R);
    expect(pts).toHaveLength(4);
    expect(pts.map((p) => p.x)).toEqual(["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]);
  });
  it("kumulierte Quote: 1. korrekt=100 %, nach 2. (1 falsch)=50 %", () => {
    const pts = equityCurve(R);
    expect(pts[0].y).toBeCloseTo(100, 5);
    expect(pts[1].y).toBeCloseTo(50, 5);
  });
  it("sortiert unabhaengig von Eingabereihenfolge", () => {
    const pts = equityCurve([R[3], R[0], R[2], R[1]]);
    expect(pts.map((p) => p.x)).toEqual(["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"]);
  });
});

describe("formatHitRate (Anzeige; UNAVAILABLE != 0)", () => {
  it("null => 'n.v.' (keine Daten, NICHT '0 %')", () => {
    expect(formatHitRate(null)).toBe("n.v.");
  });
  it("0 => '0 %' (legitim bei n>0)", () => {
    expect(formatHitRate(0)).toBe("0 %");
  });
  it("75 => '75 %' (gerundet)", () => {
    expect(formatHitRate(75)).toBe("75 %");
    expect(formatHitRate(74.6)).toBe("75 %");
  });
});
