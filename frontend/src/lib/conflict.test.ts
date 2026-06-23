import { describe, it, expect } from "vitest";
import { detectConflict, conflictNote } from "./conflict";
import type { PositionJudgmentDTO } from "../contract/portfolio";

function j(partial: Partial<PositionJudgmentDTO>): PositionJudgmentDTO {
  return { longVerdict: "HOLD", shortVerdict: "NONE", confidence: 0.5, ...partial };
}

describe("detectConflict", () => {
  it("long + Long-Verdikt SELL => Konflikt (Urteil will raus)", () => {
    expect(detectConflict("long", j({ longVerdict: "SELL" }))).toBe(true);
  });
  it("long + Short-Verdikt SHORT => Konflikt (Urteil shortet gegen Bestand)", () => {
    expect(detectConflict("long", j({ longVerdict: "NONE", shortVerdict: "SHORT" }))).toBe(true);
  });
  it("long + BUY/HOLD => kein Konflikt", () => {
    expect(detectConflict("long", j({ longVerdict: "BUY" }))).toBe(false);
    expect(detectConflict("long", j({ longVerdict: "HOLD" }))).toBe(false);
  });
  it("short + Short-Verdikt COVER => Konflikt (Urteil will eindecken)", () => {
    expect(detectConflict("short", j({ shortVerdict: "COVER" }))).toBe(true);
  });
  it("short + Long-Verdikt BUY => Konflikt (Urteil kauft gegen Short)", () => {
    expect(detectConflict("short", j({ longVerdict: "BUY", shortVerdict: "HOLD" }))).toBe(true);
  });
  it("short + SHORT/HOLD => kein Konflikt", () => {
    expect(detectConflict("short", j({ shortVerdict: "SHORT" }))).toBe(false);
    expect(detectConflict("short", j({ shortVerdict: "HOLD" }))).toBe(false);
  });
});

describe("conflictNote", () => {
  it("liefert eine Begruendung bei Konflikt, sonst null", () => {
    expect(conflictNote("long", j({ longVerdict: "SELL" }))).toMatch(/SELL/);
    expect(conflictNote("long", j({ longVerdict: "BUY" }))).toBeNull();
  });
});
