import { describe, it, expect } from "vitest";
import { MARKET_WISDOM, nextWisdomIndex, type Wisdom } from "./marketWisdom";

// Reine Inhalts-/Rotationslogik fuer das Lade-Erlebnis (#3). Keine I/O, keine Timer —
// die Rotation selbst ist eine pure Index-Funktion, der Timer ist nur ein duenner Wrapper.
describe("marketWisdom — Inhalt", () => {
  it("liefert eine ausreichend grosse, gemischte Sammlung", () => {
    expect(MARKET_WISDOM.length).toBeGreaterThanOrEqual(12);
    const kinds = new Set(MARKET_WISDOM.map((w) => w.kind));
    expect(kinds.has("weisheit")).toBe(true);
    expect(kinds.has("fakt")).toBe(true);
  });

  it("jeder Eintrag hat nicht-leeren Text und eine gueltige Art", () => {
    for (const w of MARKET_WISDOM as Wisdom[]) {
      expect(w.text.trim().length).toBeGreaterThan(0);
      expect(["weisheit", "fakt"]).toContain(w.kind);
      // author ist optional, aber wenn gesetzt, nicht leer (kein "— " ohne Name)
      if (w.author !== undefined) expect(w.author.trim().length).toBeGreaterThan(0);
    }
  });

  it("Faelle dedupliziert (keine identischen Texte)", () => {
    const texts = MARKET_WISDOM.map((w) => w.text);
    expect(new Set(texts).size).toBe(texts.length);
  });
});

describe("nextWisdomIndex — Rotation", () => {
  it("zaehlt hoch und laeuft am Ende rund", () => {
    expect(nextWisdomIndex(0, 5)).toBe(1);
    expect(nextWisdomIndex(3, 5)).toBe(4);
    expect(nextWisdomIndex(4, 5)).toBe(0); // wrap-around
  });

  it("ist robust bei Grenzfaellen (0/1 Eintrag, ausserhalb des Bereichs)", () => {
    expect(nextWisdomIndex(0, 0)).toBe(0); // leere Liste -> 0, kein Modulo-durch-0
    expect(nextWisdomIndex(0, 1)).toBe(0); // einziger Eintrag bleibt
    expect(nextWisdomIndex(99, 5)).toBe(0); // ausserhalb -> sauber zurueck auf 0
  });
});
