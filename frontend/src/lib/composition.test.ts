import { describe, it, expect } from "vitest";
import { allocationBy, longShortSplit, judgmentAlignment } from "./composition";
import type { PositionDTO } from "../contract/portfolio";

// Minimaler Positions-Builder (nur die fuer die jeweilige Mathematik relevanten Felder setzen).
function pos(over: Partial<PositionDTO>): PositionDTO {
  return {
    ticker: "X", name: "X", underlying: "equity", wrapper: "single",
    direction: "long", sizePctNav: 10, entryPrice: 1, currency: "USD",
    sector: "Tech", geography: "USA", beta: 1,
    judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 },
    ...over,
  };
}

describe("composition", () => {
  describe("allocationBy", () => {
    it("summiert |Größe| je Gruppe und rechnet den Anteil am Brutto-Exposure", () => {
      const ps = [
        pos({ underlying: "equity", sizePctNav: 30 }),
        pos({ underlying: "equity", sizePctNav: 20 }),
        pos({ underlying: "precious_metal", sizePctNav: 40 }),
        pos({ underlying: "bond", sizePctNav: 10 }),
      ];
      const slices = allocationBy(ps, "underlying");
      // Brutto = 100 -> Anteile = Roh-Punkte; absteigend sortiert.
      expect(slices.map((s) => s.name)).toEqual(["equity", "precious_metal", "bond"]);
      expect(slices[0]).toEqual({ name: "equity", grossPct: 50, sharePct: 50 });
      expect(slices[1]).toEqual({ name: "precious_metal", grossPct: 40, sharePct: 40 });
      expect(slices[2]).toEqual({ name: "bond", grossPct: 10, sharePct: 10 });
    });

    it("short-Positionen zählen positiv ins Brutto (Allokation = Markt-Engagement)", () => {
      const ps = [
        pos({ geography: "USA", direction: "long", sizePctNav: 30 }),
        pos({ geography: "Eurozone", direction: "short", sizePctNav: 10 }),
      ];
      const slices = allocationBy(ps, "geography");
      expect(slices[0]).toEqual({ name: "USA", grossPct: 30, sharePct: 75 });
      expect(slices[1]).toEqual({ name: "Eurozone", grossPct: 10, sharePct: 25 });
    });

    it("leere Eingabe -> leere Liste", () => {
      expect(allocationBy([], "sector")).toEqual([]);
    });
  });

  describe("longShortSplit", () => {
    it("trennt Brutto-Long von Brutto-Short, Netto = long − short, plus Anzahlen", () => {
      const ps = [
        pos({ direction: "long", sizePctNav: 30 }),
        pos({ direction: "long", sizePctNav: 20 }),
        pos({ direction: "short", sizePctNav: 15 }),
      ];
      expect(longShortSplit(ps)).toEqual({
        grossLongPct: 50, grossShortPct: 15, netPct: 35, longCount: 2, shortCount: 1,
      });
    });
  });

  describe("judgmentAlignment", () => {
    it("zählt Positionen im Einklang vs. Konflikt (gleiche Quelle wie Tabelle/Inbox)", () => {
      const ps = [
        pos({ direction: "long", judgment: { longVerdict: "SELL", shortVerdict: "NONE", confidence: 0.6 } }), // Konflikt
        pos({ direction: "long", judgment: { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5 } }), // ok
        pos({ direction: "short", judgment: { longVerdict: "NONE", shortVerdict: "SHORT", confidence: 0.6 } }), // ok
      ];
      expect(judgmentAlignment(ps)).toEqual({ aligned: 2, conflict: 1, total: 3 });
    });
  });
});
