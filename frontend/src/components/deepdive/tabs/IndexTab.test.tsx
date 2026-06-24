import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IndexTab } from "./IndexTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("IndexTab", () => {
  it("zeigt KGV, Breadth, Momentum und Sektorgewichte", () => {
    render(<IndexTab block={demoDeepDive("SPY").index!} />);
    expect(screen.getByText(/24,1/)).toBeInTheDocument();   // KGV (DE-Komma)
    expect(screen.getByText(/58/)).toBeInTheDocument();      // Breadth
    expect(screen.getByText(/Technologie/)).toBeInTheDocument();
    expect(screen.getByText(/30 %/)).toBeInTheDocument();    // Tech-Gewicht
  });
});
