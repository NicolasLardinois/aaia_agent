import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnomalyReport } from "./AnomalyReport";

describe("AnomalyReport", () => {
  it("zeigt Schwere und Ausreisser/Widersprueche getrennt", () => {
    render(<AnomalyReport anomaly={{ severity: "high", outliers: ["KGV |Z|=2.3"], conflicts: ["Top-Down vs Bottom-Up"] }} />);
    expect(screen.getByText(/hoch/i)).toBeInTheDocument();
    expect(screen.getByText(/KGV/)).toBeInTheDocument();
    expect(screen.getByText(/Top-Down vs Bottom-Up/)).toBeInTheDocument();
  });
});
