import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MacroDrilldown } from "./MacroDrilldown";
import { demoMacro } from "../../data/demo/cockpit";

// Stabile Loader-Konstante außerhalb des Renders (kein Refetch-Loop).
const loader = () => Promise.resolve(demoMacro());

vi.mock("../../data/cockpit", () => ({
  loadMacro: () => Promise.resolve(demoMacro()),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <MacroDrilldown loader={loader} />
    </MemoryRouter>,
  );
}

describe("MacroDrilldown", () => {
  it("zeigt USA, DE und CH (keine EU-Zeile)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByText("DE")).toBeInTheDocument();
    expect(screen.getByText("CH")).toBeInTheDocument();
    expect(screen.queryByText("EU")).not.toBeInTheDocument();
  });

  it("zeigt USA greifende Schwelle (erhoeht) und BEARISH-Badge", async () => {
    renderPage();
    // USA 3.2 % -> elevated (3–4 %) -> BEARISH
    await waitFor(() => expect(screen.getByText(/3–4 %/)).toBeInTheDocument());
    const bearishElements = screen.getAllByText("BEARISH");
    expect(bearishElements.length).toBeGreaterThanOrEqual(1);
  });

  it("zeigt DE Zielzone und BULLISH", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/1–3 % \(Zielzone\)/)).toBeInTheDocument());
    const bullish = screen.getAllByText("BULLISH");
    expect(bullish.length).toBeGreaterThanOrEqual(1);
  });

  it("zeigt CH-spezifische Schwelle (0.5–2 %)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/0\.5–2 % \(Zielzone\)/)).toBeInTheDocument());
  });

  it("zeigt Demo-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });

  it("zeigt dataDate je Region", async () => {
    renderPage();
    // Alle drei Regionen haben "2026-05"
    await waitFor(() => {
      const dates = screen.getAllByText("2026-05");
      expect(dates.length).toBeGreaterThanOrEqual(3);
    });
  });
});
