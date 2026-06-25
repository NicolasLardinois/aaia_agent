import { describe, it, expect } from "vitest";
import { AREAS } from "./welcomeContent";

describe("welcomeContent.AREAS", () => {
  it("deckt genau die fünf Hauptbereiche mit korrekten Routen ab", () => {
    expect(AREAS.map((a) => a.to)).toEqual([
      "/cockpit", "/deep-dive", "/portfolio", "/inbox", "/backtester",
    ]);
  });
  it("jeder Bereich hat eine Leitfrage und einen Bedienhinweis", () => {
    for (const a of AREAS) {
      expect(a.question.length).toBeGreaterThan(0);
      expect(a.howto.length).toBeGreaterThan(0);
      expect(a.name.length).toBeGreaterThan(0);
    }
  });
});
