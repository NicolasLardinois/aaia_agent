// frontend/src/data/inbox.test.ts
import { describe, it, expect } from "vitest";
import { loadInbox } from "./inbox";
import { detectConflict } from "../lib/conflict";
import type { PositionJudgmentDTO } from "../contract/portfolio";

// Rekonstruiert das Urteil aus dem DTO, um die Konflikt-Erkennung gegenzupruefen (eine Quelle der Wahrheit).
function judgmentOf(c: { newLongVerdict: PositionJudgmentDTO["longVerdict"]; newShortVerdict: PositionJudgmentDTO["shortVerdict"]; confidence: number }): PositionJudgmentDTO {
  return { longVerdict: c.newLongVerdict, shortVerdict: c.newShortVerdict, confidence: c.confidence };
}

describe("loadInbox (Tausch-Naht)", () => {
  it("liefert einen Demo-View (isDemo:true) mit mehreren Konflikten", async () => {
    const v = await loadInbox();
    expect(v.isDemo).toBe(true);
    expect(v.conflicts.length).toBeGreaterThanOrEqual(3);
  });
  it("enthaelt den XLE-Konflikt (long gehalten, Urteil SELL) mit Default EXIT", async () => {
    const v = await loadInbox();
    const xle = v.conflicts.find((c) => c.ticker === "XLE");
    expect(xle).toBeDefined();
    expect(xle?.direction).toBe("long");
    expect(xle?.suggestedVerdict).toBe("EXIT");
  });
  it("jeder gelistete Eintrag ist wirklich ein Konflikt (detectConflict-Wiederverwendung)", async () => {
    const v = await loadInbox();
    for (const c of v.conflicts) {
      expect(detectConflict(c.direction, judgmentOf(c))).toBe(true);
    }
  });
  it("alle Eintraege starten als offen (US30)", async () => {
    const v = await loadInbox();
    expect(v.conflicts.every((c) => c.status === "offen")).toBe(true);
  });
});
