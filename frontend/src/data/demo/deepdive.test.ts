import { describe, it, expect } from "vitest";
import { demoDeepDive, synthHistory } from "./deepdive";

describe("synthHistory", () => {
  it("ist deterministisch (gleicher Seed -> gleiche Reihe)", () => {
    const a = synthHistory(100, 30, 7);
    const b = synthHistory(100, 30, 7);
    expect(a).toEqual(b);
  });

  it("endet exakt auf dem aktuellen Kurs und hat die gewuenschte Laenge", () => {
    const h = synthHistory(232.1, 40, 1);
    expect(h).toHaveLength(40);
    expect(h[h.length - 1].close).toBe(232.1);
  });

  it("liefert nur positive Kurse (keine negativen Demo-Werte)", () => {
    const h = synthHistory(5, 60, 3);
    expect(h.every((p) => p.close > 0)).toBe(true);
  });

  it("ISO-Daten sind aufsteigend sortiert", () => {
    const h = synthHistory(50, 10, 2);
    const dates = h.map((p) => p.date);
    expect([...dates].sort()).toEqual(dates);
  });
});

describe("demoDeepDive priceHistory", () => {
  it("gefundener Titel bekommt eine Kurshistorie, die auf dem aktuellen Kurs endet", () => {
    const v = demoDeepDive("AAPL");
    expect(v.priceHistory && v.priceHistory.length).toBeGreaterThan(0);
    expect(v.priceHistory![v.priceHistory!.length - 1].close).toBe(v.price);
  });

  it("unbekannter Ticker (kein Kurs) bekommt keine Historie", () => {
    const v = demoDeepDive("ZZZZ");
    expect(v.found).toBe(false);
    expect(v.priceHistory).toBeUndefined();
  });
});
