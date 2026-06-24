import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CommoditiesDrilldown } from "./CommoditiesDrilldown";
import { demoCommodities } from "../../data/demo/cockpit";

const loader = () => Promise.resolve(demoCommodities());

function renderPage() {
  return render(
    <MemoryRouter>
      <CommoditiesDrilldown loader={loader} />
    </MemoryRouter>,
  );
}

describe("CommoditiesDrilldown", () => {
  it("zeigt Rohoel (WTI) mit BULLISH", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Rohoel/i)).toBeInTheDocument());
    expect(screen.getByText("BULLISH")).toBeInTheDocument();
  });

  it("zeigt Kupfer mit BEARISH", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Kupfer")).toBeInTheDocument());
    expect(screen.getByText("BEARISH")).toBeInTheDocument();
  });

  it("zeigt Erdgas mit NEUTRAL", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Erdgas")).toBeInTheDocument());
    expect(screen.getByText("NEUTRAL")).toBeInTheDocument();
  });

  it("zeigt Demo-Badge", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Demo-Daten")).toBeInTheDocument());
  });

  it("zeigt Notizen (Note-Text)", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/Angebotsdisziplin OPEC\+/i)).toBeInTheDocument());
  });
});
