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
});
