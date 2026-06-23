import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EquityTabs } from "./EquityTabs";
import { demoDeepDive } from "../../../data/demo/deepdive";

const block = demoDeepDive("AAPL").equity!;

describe("EquityTabs", () => {
  it("Bewertung: zeigt KGV, EV/EBITDA und kombinierte Bandbreite", () => {
    render(<EquityTabs block={block} tab="valuation" />);
    expect(screen.getByText(/30\.5/)).toBeInTheDocument(); // KGV
    expect(screen.getByText(/22\.4/)).toBeInTheDocument(); // EV/EBITDA
    // kombiniertes Band: prüfe den eindeutigen Label-Kontext + Werte
    expect(screen.getByText(/Kombinierte Bandbreite:/)).toBeInTheDocument();
    expect(screen.getByText((_, el) => (el?.textContent === "170–210" && el?.className.includes("font-medium")))).toBeInTheDocument();
  });
  it("Qualität: Altman-Z 6.1 (Technology -> Z'') => solvent", () => {
    render(<EquityTabs block={block} tab="quality" />);
    expect(screen.getByText(/6\.1/)).toBeInTheDocument();
    expect(screen.getByText(/solvent/i)).toBeInTheDocument();
  });
  it("Signale: Earnings-Trend null => nicht verfügbar (NICHT neutral/0)", () => {
    render(<EquityTabs block={block} tab="signals" />);
    expect(screen.getByText(/Moat/i)).toBeInTheDocument();
    expect(screen.getAllByText(/nicht verfügbar/i).length).toBeGreaterThanOrEqual(1);
  });
});
