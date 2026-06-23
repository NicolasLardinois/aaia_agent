import { describe, it, expect } from "vitest";
import { detectKlumpen, DEFAULT_LIMITS } from "./klumpen";
import type { PositionDTO } from "../contract/portfolio";

function p(partial: Partial<PositionDTO>): PositionDTO {
  return {
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 10, entryPrice: 100, currency: "USD",
    sector: "Technologie", geography: "USA", beta: 1,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 },
    ...partial,
  };
}
const dims = (ws: ReturnType<typeof detectKlumpen>) => ws.map((w) => w.dimension);

describe("detectKlumpen", () => {
  it("leeres Portfolio => keine Warnungen (kein Division-durch-0)", () => {
    expect(detectKlumpen([])).toEqual([]);
  });
  it("Sektor genau auf dem Limit (0.40) => KEINE Warnung (strikt groesser)", () => {
    // 40 Tech von 100 Brutto = 0.40 == Limit -> keine Warnung.
    // Gesundheit (20) + Energie (20) + Finanzen (20) je 20 % < Limit -> auch kein Alarm.
    // Abweichung vom Plan: Original hatte nur 2 Sektoren (40+60), aber Gesundheit (60 %)
    // haette selbst ein Sektor-Alarm ausgeloest (60 % > 40 %-Limit). Drei kleinere
    // Gegensektoren a 20 % behalten den Testintent (genau auf Limit = kein Alarm).
    const out = detectKlumpen([
      p({ sector: "Technologie", sizePctNav: 40 }),
      p({ sector: "Gesundheit", sizePctNav: 20 }),
      p({ sector: "Energie", sizePctNav: 20 }),
      p({ sector: "Finanzen", sizePctNav: 20 }),
    ]);
    expect(dims(out).filter((d) => d === "sector")).toHaveLength(0);
  });
  it("Sektor knapp ueber Limit (0.41) => Sektor-Warnung mit Limit-Bezug", () => {
    const out = detectKlumpen([
      p({ sector: "Technologie", sizePctNav: 41 }),
      p({ sector: "Gesundheit", sizePctNav: 59 }),
    ]);
    const tech = out.find((w) => w.dimension === "sector" && w.name === "Technologie");
    expect(tech).toBeTruthy();
    expect(tech!.limit).toBe(DEFAULT_LIMITS.sector);
    expect(tech!.message).toMatch(/Technologie/);
    expect(tech!.message).toMatch(/Limit/);
  });
  it("Gegenlaeufige Position senkt die Netto-Konzentration (Hedge zaehlt netto)", () => {
    // 50 long USA + 30 short USA = netto 20 / Brutto 80 = 0.25 < 0.70 -> keine USA-Warnung
    const out = detectKlumpen([
      p({ geography: "USA", direction: "long", sizePctNav: 50 }),
      p({ geography: "USA", direction: "short", sizePctNav: 30 }),
    ]);
    expect(out.find((w) => w.dimension === "geography" && w.name === "USA")).toBeUndefined();
  });
  it("underlying-Klumpen (equity > 0.60) wird erkannt", () => {
    const out = detectKlumpen([
      p({ underlying: "equity", sizePctNav: 70 }),
      p({ underlying: "bond", sizePctNav: 30 }),
    ]);
    expect(out.find((w) => w.dimension === "underlying" && w.name === "equity")).toBeTruthy();
  });
});
