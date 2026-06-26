import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { HexagonSpinner } from "./HexagonSpinner";

// Der Hexagon-Spinner ist reine Praesentation (Bezug zur hexagonalen Architektur):
// ein leuchtendes Segment wandert ueber die sechs Kanten. Standard = dekorativ.
describe("HexagonSpinner", () => {
  it("rendert ein SVG mit der sechseckigen Grundform", () => {
    const { container } = render(<HexagonSpinner />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    // ein Sechseck = polygon mit sechs Eckpunkt-Paaren
    const polygons = container.querySelectorAll("polygon");
    expect(polygons.length).toBeGreaterThanOrEqual(1);
    const pts = polygons[0].getAttribute("points") ?? "";
    expect(pts.trim().split(/\s+/).length).toBe(6);
  });

  it("ist standardmaessig dekorativ (aria-hidden) und nicht als Bild ausgezeichnet", () => {
    const { container } = render(<HexagonSpinner />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("role")).not.toBe("img");
  });

  it("reicht className durch (Groesse/Farbe steuerbar)", () => {
    const { container } = render(<HexagonSpinner className="h-20 w-20 text-brand" />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("class")).toContain("h-20");
    expect(svg.getAttribute("class")).toContain("text-brand");
  });
});
