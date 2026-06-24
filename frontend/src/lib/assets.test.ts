import { describe, it, expect } from "vitest";
import { underlyingToVisual, wrapperToVisual } from "./assets";

describe("underlyingToVisual", () => {
  it("liefert Label + Icon je Basiswert", () => {
    expect(underlyingToVisual("precious_metal")).toMatchObject({ label: "Edelmetall", icon: "🥇" });
    expect(underlyingToVisual("equity")).toMatchObject({ label: "Aktie", icon: "🏢" });
    expect(underlyingToVisual("equity_index")).toMatchObject({ label: "Index", icon: "📈" });
    expect(underlyingToVisual("bond")).toMatchObject({ label: "Anleihe", icon: "🏛" });
    expect(underlyingToVisual("commodity")).toMatchObject({ label: "Rohstoff", icon: "🛢" });
  });
});

describe("wrapperToVisual", () => {
  it("liefert Label + Icon je Huelle", () => {
    expect(wrapperToVisual("future")).toMatchObject({ label: "Future", icon: "⏳" });
    expect(wrapperToVisual("single")).toMatchObject({ label: "Einzeltitel" });
    expect(wrapperToVisual("fund")).toMatchObject({ label: "Fonds" });
    expect(wrapperToVisual("physical_etc")).toMatchObject({ label: "Physisch (ETC)" });
  });
});
