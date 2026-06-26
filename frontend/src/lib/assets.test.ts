import { describe, it, expect } from "vitest";
import { underlyingToVisual, wrapperToVisual } from "./assets";

describe("underlyingToVisual", () => {
  it("liefert Label + semantischen Icon-Namen je Basiswert", () => {
    expect(underlyingToVisual("precious_metal")).toMatchObject({ label: "Edelmetall", icon: "asset-precious-metal" });
    expect(underlyingToVisual("equity")).toMatchObject({ label: "Aktie", icon: "asset-equity" });
    expect(underlyingToVisual("equity_index")).toMatchObject({ label: "Index", icon: "asset-index" });
    expect(underlyingToVisual("bond")).toMatchObject({ label: "Anleihe", icon: "asset-bond" });
    expect(underlyingToVisual("commodity")).toMatchObject({ label: "Rohstoff", icon: "asset-commodity" });
  });
});

describe("wrapperToVisual", () => {
  it("liefert Label + semantischen Icon-Namen je Huelle", () => {
    expect(wrapperToVisual("future")).toMatchObject({ label: "Future", icon: "wrap-future" });
    expect(wrapperToVisual("single")).toMatchObject({ label: "Einzeltitel", icon: "wrap-single" });
    expect(wrapperToVisual("fund")).toMatchObject({ label: "Fonds", icon: "wrap-fund" });
    expect(wrapperToVisual("physical_etc")).toMatchObject({ label: "Physisch (ETC)", icon: "wrap-physical" });
  });
});
