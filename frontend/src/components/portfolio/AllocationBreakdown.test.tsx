import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AllocationBreakdown } from "./AllocationBreakdown";

describe("AllocationBreakdown", () => {
  it("zeigt Titel, Namen und Anteile", () => {
    render(<AllocationBreakdown title="Sektor" slices={[
      { name: "Technologie", sharePct: 47.4 },
      { name: "Anleihen", sharePct: 17.5 },
    ]} />);
    expect(screen.getByText("Sektor")).toBeInTheDocument();
    expect(screen.getByText("Technologie")).toBeInTheDocument();
    expect(screen.getByText("47.4 %")).toBeInTheDocument();
    expect(screen.getByText("Anleihen")).toBeInTheDocument();
  });

  it("wendet labelFor auf den Namen an (z. B. underlying-Key -> deutsch)", () => {
    render(<AllocationBreakdown title="Asset-Klasse" slices={[{ name: "equity", sharePct: 56.1 }]}
      labelFor={(n) => (n === "equity" ? "Aktie" : n)} />);
    expect(screen.getByText("Aktie")).toBeInTheDocument();
    expect(screen.queryByText("equity")).toBeNull();
  });

  it("leere Liste -> Hinweis statt Balken", () => {
    render(<AllocationBreakdown title="Geographie" slices={[]} />);
    expect(screen.getByText(/Keine Positionen/i)).toBeInTheDocument();
  });
});
