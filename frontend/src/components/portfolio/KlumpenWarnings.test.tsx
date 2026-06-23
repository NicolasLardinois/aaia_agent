import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KlumpenWarnings } from "./KlumpenWarnings";
import type { KlumpenWarningDTO } from "../../contract/portfolio";

const tech: KlumpenWarningDTO = {
  dimension: "sector", name: "Technologie", pct: 0.41, limit: 0.30, message: "Technologie 41 % (Limit 30 %)",
};

describe("KlumpenWarnings", () => {
  it("zeigt jede Warnung mit deutscher Dimension und Limit-Bezug", () => {
    render(<KlumpenWarnings klumpen={[tech]} />);
    expect(screen.getByText(/Sektor/)).toBeInTheDocument();
    expect(screen.getByText(/Technologie 41 % \(Limit 30 %\)/)).toBeInTheDocument();
  });
  it("leere Liste => Entwarnung statt Warnung", () => {
    render(<KlumpenWarnings klumpen={[]} />);
    expect(screen.getByText(/Keine Konzentration über den Limits/i)).toBeInTheDocument();
  });
});
