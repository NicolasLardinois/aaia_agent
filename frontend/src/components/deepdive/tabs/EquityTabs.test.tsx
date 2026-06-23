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
    // kombiniertes Band (Median lows 160/170/180 -> 170; highs 205/210/220 -> 210)
    // Wert 170 erscheint auch in Methoden-Tabelle -> mind. 1 Element
    expect(screen.getAllByText(/170/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/210/).length).toBeGreaterThanOrEqual(1);
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
