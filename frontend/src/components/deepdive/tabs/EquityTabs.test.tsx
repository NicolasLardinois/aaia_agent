import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EquityTabs } from "./EquityTabs";
import { demoDeepDive } from "../../../data/demo/deepdive";

const block = demoDeepDive("AAPL").equity!;

describe("EquityTabs", () => {
  it("Bewertung: zeigt KGV, EV/EBITDA und kombinierte Bandbreite", () => {
    render(<EquityTabs block={block} tab="valuation" />);
    expect(screen.getByText(/30,5/)).toBeInTheDocument(); // KGV (DE-Komma)
    expect(screen.getByText(/22,4/)).toBeInTheDocument(); // EV/EBITDA (DE-Komma)
    // kombiniertes Band: prüfe den eindeutigen Label-Kontext + Werte
    expect(screen.getByText(/Kombinierte Bandbreite:/)).toBeInTheDocument();
    expect(screen.getByText((_, el) => (el?.textContent === "170–210" && el?.className.includes("font-medium")))).toBeInTheDocument();
  });
  it("Qualität: Altman-Z 6.1 (Technology -> Z'') => solvent", () => {
    render(<EquityTabs block={block} tab="quality" />);
    expect(screen.getByText(/6,1/)).toBeInTheDocument(); // Altman-Z (DE-Komma)
    expect(screen.getByText(/solvent/i)).toBeInTheDocument();
  });
  it("Signale: Earnings-Trend null => nicht verfügbar (NICHT neutral/0)", () => {
    render(<EquityTabs block={block} tab="signals" />);
    expect(screen.getByText(/Moat/i)).toBeInTheDocument();
    expect(screen.getAllByText(/nicht verfügbar/i).length).toBeGreaterThanOrEqual(1);
  });

  // --- Teil-Projekt B1: erweiterter Kennzahlen-Katalog ---
  it("Bewertung: zeigt die erweiterten Kennzahlen + Erklär-Tooltips", () => {
    render(<EquityTabs block={block} tab="valuation" />);
    expect(screen.getByText("Forward-KGV")).toBeInTheDocument();
    expect(screen.getByText("Shiller-CAPE")).toBeInTheDocument();
    expect(screen.getByText("Dividendenrendite")).toBeInTheDocument();
    expect(screen.getByText("KBV")).toBeInTheDocument();
    // mindestens ein Fachbegriff-Tooltip ist eingebunden (A-Baukasten)
    expect(screen.getAllByRole("button", { name: /Erklärung:/i }).length).toBeGreaterThan(0);
  });

  it("Bewertung: PEG ist im Demo null => 'n.v.' (UNAVAILABLE ≠ 0)", () => {
    render(<EquityTabs block={block} tab="valuation" />);
    expect(screen.getByText("PEG")).toBeInTheDocument();
    expect(screen.getByText("n.v.")).toBeInTheDocument();
  });

  it("Qualität: zeigt zusätzlich WACC, Umsatzwachstum und Verschuldungsgrad", () => {
    render(<EquityTabs block={block} tab="quality" />);
    // über die eindeutige InfoTip-Beschriftung prüfen (Tooltip-Texte enthalten teils dieselben Wörter)
    expect(screen.getByRole("button", { name: "Erklärung: WACC" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Erklärung: Umsatzwachstum" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Erklärung: Verschuldungsgrad" })).toBeInTheDocument();
  });

  it("ohne fundamentals-Block: kein Crash, KGV weiterhin sichtbar", () => {
    const ohneF = { ...block, fundamentals: undefined };
    render(<EquityTabs block={ohneF} tab="valuation" />);
    expect(screen.getByText("KGV")).toBeInTheDocument();
  });
});
