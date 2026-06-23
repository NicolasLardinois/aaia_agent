import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExposurePanel } from "./ExposurePanel";
import type { ExposureDTO } from "../../contract/portfolio";

const exp: ExposureDTO = {
  grossPct: 142, netPct: 38, netBeta: 62, annualizedVolPct: 13.8, volAsOf: "2026-06-20",
};

describe("ExposurePanel", () => {
  it("zeigt Brutto, Netto und net_beta mit Inline-Definitionen", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/142/)).toBeInTheDocument();
    expect(screen.getByText(/\+38/)).toBeInTheDocument();          // Netto mit Vorzeichen
    expect(screen.getByText(/62/)).toBeInTheDocument();            // net_beta
    expect(screen.getByText(/Σ\|Position\|/)).toBeInTheDocument(); // Brutto-Definition
    expect(screen.getByText(/long − short/)).toBeInTheDocument();  // Netto-Definition
  });
  it("kennzeichnet net_beta als aktien-only (Pflicht-Label)", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/aktien-only/i)).toBeInTheDocument();
  });
  it("zeigt die datierte Vola (Stand)", () => {
    render(<ExposurePanel exposure={exp} />);
    expect(screen.getByText(/2026-06-20/)).toBeInTheDocument();
  });
  it("zeigt 'nicht verfügbar' wenn Vola null (nie als 0)", () => {
    render(<ExposurePanel exposure={{ ...exp, annualizedVolPct: null }} />);
    expect(screen.getByText(/nicht verfügbar/i)).toBeInTheDocument();
  });
});
