import { describe, it, expect } from "vitest";
import { glossaryLookup } from "./glossary";

describe("glossaryLookup", () => {
  it("liefert eine deutsche Erklärung für einen bekannten Begriff", () => {
    const text = glossaryLookup("Top-Down");
    expect(text).toBeTruthy();
    expect(text).toContain("oben");
  });
  it("liefert null für einen unbekannten Begriff", () => {
    expect(glossaryLookup("Quatschbegriff")).toBeNull();
  });

  it("erklärt die Anlage-Philosophie (Long-Short + Total-Return)", () => {
    // Long-Short: Kern-Grundsatz — Short ist NICHT das Spiegelbild eines Longs.
    const ls = glossaryLookup("Long-Short");
    expect(ls).toBeTruthy();
    expect(ls).toContain("Spiegelbild");
    // Total-Return: fachlich korrekt = Kursveränderung + Erträge (Dividenden/Zinsen).
    const tr = glossaryLookup("Total-Return");
    expect(tr).toBeTruthy();
    expect(tr).toMatch(/Dividend|Erträge|Ausschüttung/);
  });

  it("erklärt die Deep-Dive-Aktienkennzahlen (Teil-Projekt B1)", () => {
    const terms = [
      "KGV", "Forward-KGV", "Shiller-CAPE", "PEG", "EV/EBITDA", "EV/Umsatz",
      "KBV", "KUV", "P/FCF", "Dividendenrendite", "WACC", "ROIC",
      "Bruttomarge", "Operative Marge", "Umsatzwachstum", "Verschuldungsgrad",
      "Altman-Z", "Short-Interest", "Moat",
    ];
    for (const t of terms) {
      expect(glossaryLookup(t), `Glossar-Eintrag fehlt: ${t}`).toBeTruthy();
    }
  });
});
