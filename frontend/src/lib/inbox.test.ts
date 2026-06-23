// frontend/src/lib/inbox.test.ts
import { describe, it, expect } from "vitest";
import { suggestVerdict, openCount } from "./inbox";

describe("suggestVerdict (beratender Default, US29)", () => {
  it("long + neues SHORT => REVERSE (aktives Gegen-Setup)", () => {
    expect(suggestVerdict("long", "BUY", "HOLD", "SHORT").verdict).toBe("REVERSE");
  });
  it("long + SELL ohne SHORT => EXIT", () => {
    expect(suggestVerdict("long", "BUY", "SELL", "NONE").verdict).toBe("EXIT");
  });
  it("long ohne echtes Gegensignal => HOLD", () => {
    expect(suggestVerdict("long", "BUY", "HOLD", "NONE").verdict).toBe("HOLD");
  });
  it("short + neues BUY => REVERSE", () => {
    expect(suggestVerdict("short", "SHORT", "BUY", "HOLD").verdict).toBe("REVERSE");
  });
  it("short + COVER ohne BUY => EXIT", () => {
    expect(suggestVerdict("short", "SHORT", "NONE", "COVER").verdict).toBe("EXIT");
  });
  it("short ohne echtes Gegensignal => HOLD", () => {
    expect(suggestVerdict("short", "SHORT", "NONE", "HOLD").verdict).toBe("HOLD");
  });
  it("liefert immer eine nicht-leere Begruendung", () => {
    expect(suggestVerdict("long", "BUY", "SELL", "NONE").rationale.length).toBeGreaterThan(0);
  });
  // Grenzfaelle: long mit SELL + SHORT gleichzeitig => SHORT hat Vorrang (REVERSE)
  it("long + SELL + SHORT => REVERSE (SHORT hat Vorrang vor SELL)", () => {
    expect(suggestVerdict("long", "BUY", "SELL", "SHORT").verdict).toBe("REVERSE");
  });
  // Grenzfaelle: short mit COVER + BUY gleichzeitig => BUY hat Vorrang (REVERSE)
  it("short + COVER + BUY => REVERSE (BUY hat Vorrang vor COVER)", () => {
    expect(suggestVerdict("short", "SHORT", "BUY", "COVER").verdict).toBe("REVERSE");
  });
  // Grenzfall: long mit NONE/NONE => HOLD
  it("long + NONE/NONE => HOLD", () => {
    expect(suggestVerdict("long", "BUY", "NONE", "NONE").verdict).toBe("HOLD");
  });
  // Grenzfall: short mit NONE/NONE => HOLD
  it("short + NONE/NONE => HOLD", () => {
    expect(suggestVerdict("short", "SHORT", "NONE", "NONE").verdict).toBe("HOLD");
  });
});

describe("openCount (Badge-Zahl, US28)", () => {
  it("zaehlt nur offene Konflikte", () => {
    expect(openCount([{ status: "offen" }, { status: "erledigt" }, { status: "offen" }])).toBe(2);
  });
  it("leere Liste => 0 (legitime Null, kein UNAVAILABLE)", () => {
    expect(openCount([])).toBe(0);
  });
  it("alle erledigt => 0", () => {
    expect(openCount([{ status: "erledigt" }, { status: "erledigt" }])).toBe(0);
  });
  it("alle offen => volle Zahl", () => {
    expect(openCount([{ status: "offen" }, { status: "offen" }, { status: "offen" }])).toBe(3);
  });
});
