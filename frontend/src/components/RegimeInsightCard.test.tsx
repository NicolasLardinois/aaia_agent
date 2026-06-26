import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegimeInsightCard } from "./RegimeInsightCard";

describe("RegimeInsightCard", () => {
  it("erklaert eine bekannte Phase mit Vorteil + Vorsicht", () => {
    render(<RegimeInsightCard regime="Aufschwung" />);
    expect(screen.getByText(/Was bedeutet Aufschwung/i)).toBeInTheDocument();
    expect(screen.getByText(/Im Vorteil/i)).toBeInTheDocument();
    expect(screen.getByText(/Vorsicht/i)).toBeInTheDocument();
    // favored-Text der Aufschwung-Phase
    expect(screen.getByText(/Aktien fuehren|zyklisch/i)).toBeInTheDocument();
  });

  it("faellt bei unbekanntem Regime sichtbar zurueck", () => {
    render(<RegimeInsightCard regime="Foobar" />);
    expect(screen.getByText(/keine hinterlegte Deutung/i)).toBeInTheDocument();
  });
});
