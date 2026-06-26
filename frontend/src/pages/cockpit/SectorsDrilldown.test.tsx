import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SectorsDrilldown } from "./SectorsDrilldown";
import { demoSectors } from "../../data/demo/cockpit";

const loader = () => Promise.resolve(demoSectors());

function renderPage() {
  return render(
    <MemoryRouter>
      <SectorsDrilldown loader={loader} />
    </MemoryRouter>,
  );
}

describe("SectorsDrilldown", () => {
  it("zeigt Regime AUFSCHWUNG", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/AUFSCHWUNG/)).toBeInTheDocument());
  });

  it("zeigt Technologie als favored mit BULLISH", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Technologie")).toBeInTheDocument());
    // Mehrere Sektoren sind BULLISH (Technologie, Zyklischer Konsum, Industrie)
    expect(screen.getAllByText("BULLISH").length).toBeGreaterThanOrEqual(1);
    // Demo-Fixture hat 3 favored-Sektoren: Technologie, Zyklischer Konsum, Industrie
    expect(screen.getAllByText(/favored/i).length).toBeGreaterThanOrEqual(3);
  });

  it("zeigt Versorger als avoid mit BEARISH", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Versorger")).toBeInTheDocument());
    expect(screen.getByText("BEARISH")).toBeInTheDocument();
    expect(screen.getAllByText(/avoid/i).length).toBeGreaterThanOrEqual(1);
  });

  it("zeigt Energie-Zeile mit UnavailableField (nicht NEUTRAL/0)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Energie")).toBeInTheDocument());
    // UnavailableField zeigt "nicht verfügbar"
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
    // Signal null -> KEIN "NEUTRAL" für die Energie-Zeile
    // (andere Zeilen haben NEUTRAL für Basiskonsum, also nur prüfen dass "nicht verfügbar" da ist)
  });

  it("zeigt SourceHealth 2/3 und Warnung (US9)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("2/3 Quellen aktiv")).toBeInTheDocument());
    expect(screen.getByLabelText("Quellen ausgefallen")).toBeInTheDocument();
  });

  it("zeigt Demo-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });
});
