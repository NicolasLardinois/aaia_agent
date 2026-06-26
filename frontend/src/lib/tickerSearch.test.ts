import { describe, it, expect } from "vitest";
import { searchTickers, resolveTicker } from "./tickerSearch";

describe("searchTickers / resolveTicker", () => {
  it("löst den Tippfehler 'appl' auf AAPL auf (Bug #10)", () => {
    expect(resolveTicker("appl")).toBe("AAPL");
  });

  it("findet über den Namen: 'apple' → AAPL", () => {
    expect(resolveTicker("apple")).toBe("AAPL");
  });

  it("toleriert größere Tippfehler über Levenshtein: 'mecrosoft' → MSFT", () => {
    expect(resolveTicker("mecrosoft")).toBe("MSFT");
  });

  it("matcht exakte Symbole case-insensitiv: 'aapl' und 'AAPL' → AAPL", () => {
    expect(resolveTicker("aapl")).toBe("AAPL");
    expect(resolveTicker("AAPL")).toBe("AAPL");
  });

  it("findet über Synonyme/Aliasse: 'oel' und 'oil' → CL=F", () => {
    expect(resolveTicker("oel")).toBe("CL=F");
    expect(resolveTicker("oil")).toBe("CL=F");
  });

  it("ignoriert Sonderzeichen/Leerzeichen: 's&p' → SPY", () => {
    expect(resolveTicker("s&p")).toBe("SPY");
    expect(resolveTicker("sp 500")).toBe("SPY");
  });

  it("'gold' liefert beide Gold-Hüllen, GC=F (exakter Alias) zuerst", () => {
    const hits = searchTickers("gold");
    const tickers = hits.map((h) => h.entry.ticker);
    expect(tickers).toContain("GC=F");
    expect(tickers).toContain("4GLD");
    expect(tickers[0]).toBe("GC=F");
  });

  it("gibt für leere Eingabe keine Treffer und null zurück", () => {
    expect(searchTickers("")).toEqual([]);
    expect(searchTickers("   ")).toEqual([]);
    expect(resolveTicker("")).toBeNull();
  });

  it("gibt für reinen Unsinn keinen Treffer", () => {
    expect(resolveTicker("zzzzqqqqxxxx")).toBeNull();
  });

  it("begrenzt die Trefferzahl über das Limit", () => {
    expect(searchTickers("a", 3).length).toBeLessThanOrEqual(3);
  });

  it("sortiert absteigend nach Score (bester Treffer zuerst)", () => {
    const hits = searchTickers("apple");
    for (let i = 1; i < hits.length; i++) {
      expect(hits[i - 1].score).toBeGreaterThanOrEqual(hits[i].score);
    }
  });
});
