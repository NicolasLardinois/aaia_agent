import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./routes";

// Cockpit-Datenhook neutralisieren (kein echter Netz-Call im Routing-Test).
vi.mock("./hooks/useCockpit", () => ({
  useCockpit: () => ({ overview: null, phase: "ready", error: null, events: [], startAnalysis: () => {} }),
}));

// ECharts im jsdom neutralisieren (LineCurve in YieldCurveDrilldown).
vi.mock("echarts-for-react", () => ({ default: () => null }));

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>);
}

describe("AppRoutes", () => {
  it("zeigt Portfolio-Platzhalter unter /portfolio", () => {
    renderAt("/portfolio");
    expect(screen.getByRole("heading", { name: /Portfolio/i })).toBeInTheDocument();
    expect(screen.getByText(/in einem folgenden Slice/i)).toBeInTheDocument();
  });

  it("leitet / auf das Cockpit", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { name: /Cockpit — Übersicht/i })).toBeInTheDocument();
  });

  // Drilldown-Routen (B7)
  it("Navigation zu /cockpit/macro rendert Makro-Drilldown", async () => {
    renderAt("/cockpit/macro");
    await waitFor(() => expect(screen.getByText(/Makro/i)).toBeInTheDocument());
    // Zurück-Link vorhanden
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("Navigation zu /cockpit/yield-curve rendert Zinskurve-Drilldown", async () => {
    renderAt("/cockpit/yield-curve");
    await waitFor(() => expect(screen.getByText(/Zinskurve/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("Navigation zu /cockpit/commodities rendert Rohstoffe-Drilldown", async () => {
    renderAt("/cockpit/commodities");
    await waitFor(() => expect(screen.getByText(/Rohstoffe/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("Navigation zu /cockpit/sentiment rendert Sentiment-Drilldown", async () => {
    renderAt("/cockpit/sentiment");
    await waitFor(() => expect(screen.getByText(/Sentiment/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("Navigation zu /cockpit/sectors rendert Sektoren-Drilldown", async () => {
    renderAt("/cockpit/sectors");
    await waitFor(() => expect(screen.getByText(/Sektor/i)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });
});
