import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CommodityTab } from "./CommodityTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("CommodityTab", () => {
  it("Öl (CL=F): COT-Index 72 + bearish, Saisonalität leer => nicht verfügbar", () => {
    render(<CommodityTab block={demoDeepDive("CL=F").commodity!} />);
    expect(screen.getByText(/72/)).toBeInTheDocument();             // COT-Index
    expect(screen.getByText(/konträr/i)).toBeInTheDocument();       // konträre Erklärung
    expect(screen.getByText(/nicht verfügbar/i)).toBeInTheDocument(); // leere Saisonalität
  });
  it("Gold (GC=F): Cross-Metal-Ratio sichtbar, COT null => nicht verfügbar", () => {
    render(<CommodityTab block={demoDeepDive("GC=F").commodity!} />);
    expect(screen.getByText(/Gold\/Silber-Ratio/)).toBeInTheDocument();
    expect(screen.getByText(/84/)).toBeInTheDocument();
  });
});
