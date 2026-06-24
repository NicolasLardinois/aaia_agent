import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BondTab } from "./BondTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("BondTab", () => {
  it("zeigt Duration (16.2, hoch), Rating und Spread", () => {
    render(<BondTab block={demoDeepDive("TLT").bond!} />);
    expect(screen.getByText(/16,2/)).toBeInTheDocument(); // Duration (DE-Komma)
    expect(screen.getByText(/hoch/i)).toBeInTheDocument();   // Duration-Risiko
    expect(screen.getByText(/AA\+/)).toBeInTheDocument();    // Rating
    expect(screen.getByText(/5 bps/)).toBeInTheDocument();   // Spread
  });
  it("zeigt 'nicht verfügbar' bei fehlender Duration", () => {
    render(<BondTab block={{ modifiedDuration: null, creditRating: null, spreadBps: null }} />);
    expect(screen.getAllByText(/nicht verfügbar/i).length).toBeGreaterThanOrEqual(2);
  });
});
