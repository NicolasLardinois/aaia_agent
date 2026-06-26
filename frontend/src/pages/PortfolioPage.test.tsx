import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PortfolioPage } from "./PortfolioPage";
import { loadPortfolio } from "../data/portfolio";

function renderPage() {
  return render(
    <MemoryRouter>
      <PortfolioPage loader={loadPortfolio} />
    </MemoryRouter>,
  );
}

describe("PortfolioPage", () => {
  it("rendert Exposure-Panel, Klumpen, Hedge-Vorschläge und Positionstabelle", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Brutto-Exposure/)).toBeInTheDocument());
    expect(screen.getByText(/aktien-only\)/i)).toBeInTheDocument();         // net_beta-Label eindeutig (endet mit ")")
    expect(screen.getByText(/Klumpen-Warnungen/)).toBeInTheDocument();
    expect(screen.getByText(/beratend, keine Ausführung/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /AAPL/ })).toBeInTheDocument(); // Positionstabelle
  });
  it("zeigt das Demo-Etikett (isDemo)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });
  it("markiert den Konflikt (XLE) in der Tabelle", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Urteil gegen Position/i)).toBeInTheDocument());
  });
  it("zeigt Überblick, Allokations-Aufschlüsselung und Long/Short-Balance", async () => {
    renderPage();
    // Allokations-Karte mit allen drei Dimensionen
    await waitFor(() => expect(screen.getByText("Allokation")).toBeInTheDocument());
    // Dimensions-Ueberschriften der Allokations-Karte (als Headings adressiert — die
    // Begriffe "Sektor"/"Geographie" kommen auch in den Klumpen-Warnungen vor).
    expect(screen.getByRole("heading", { name: "Asset-Klasse" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sektor" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Geographie" })).toBeInTheDocument();
    // Long/Short-Balance aus den Demo-Positionen (52 % long, 5 Long-Positionen)
    expect(screen.getByText(/Long 52 % · 5/)).toBeInTheDocument();
    // Einklang-Zusammenfassung ueber der Tabelle (5 von 6 ohne Konflikt)
    expect(screen.getByText(/5 von 6 im Einklang mit dem AAIA-Urteil/)).toBeInTheDocument();
  });
});
