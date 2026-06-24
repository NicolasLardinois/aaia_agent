import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./routes";
import { demoInbox } from "./data/demo/inbox";

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
  it("/portfolio rendert die PortfolioPage (Exposure-Panel sichtbar)", async () => {
    renderAt("/portfolio"); // bestehender Render-Helfer der Datei
    await waitFor(() => expect(screen.getByText(/Brutto-Exposure/)).toBeInTheDocument());
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

  // Dispatch C: Buffett + Big-Mac-Routen (C3)
  it("Navigation zu /cockpit/buffett rendert Buffett-Widget (Tabelle)", async () => {
    renderAt("/cockpit/buffett");
    await waitFor(() => expect(screen.getByText(/Buffett/i)).toBeInTheDocument());
    // Tabelle-Default: USA-Zeile sichtbar
    await waitFor(() => expect(screen.getByText("USA")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("Navigation zu /cockpit/big-mac rendert Big-Mac-Widget", async () => {
    renderAt("/cockpit/big-mac");
    await waitFor(() => expect(screen.getByText(/Big-Mac/i)).toBeInTheDocument());
    // Publikationsdatum sichtbar
    await waitFor(() => expect(screen.getByText(/2026-01/)).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /zurück/i })).toBeInTheDocument();
  });

  it("/deep-dive/AAPL rendert die DeepDivePage", async () => {
    renderAt("/deep-dive/AAPL");
    await waitFor(() => expect(screen.getByText(/Apple/)).toBeInTheDocument());
  });

  // B3: /inbox rendert InboxPage (US28/US30)
  it("/inbox rendert die InboxPage (Ueberschrift sichtbar)", async () => {
    renderAt("/inbox");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Konflikt-Inbox/i })).toBeInTheDocument(),
    );
  });

  // B4: /backtester rendert BacktesterPage (drei Bereichs-Karten-Titel sichtbar)
  it("/backtester rendert die BacktesterPage (drei Karten)", async () => {
    renderAt("/backtester");
    await screen.findByText(/Top-Down/i);
    await screen.findByText(/Bottom-Up/i);
    await screen.findByText(/Judgment/i);
  });

  // B3: Topbar-Badge zeigt die echte offene Konflikt-Anzahl (Demo-Fixture aus demoInbox)
  it("Topbar-Badge zeigt die echte offene Konflikt-Anzahl aus Fixture", async () => {
    renderAt("/cockpit");
    // loadInboxCount laedt asynchron; Badge erscheint nach Promise-Aufloesung
    const erwartet = demoInbox().conflicts.filter((c) => c.status === "offen").length;
    await waitFor(() => {
      // Das Inbox-Badge zeigt die Zahl als Text in der Topbar (aria-label=Inbox + Badge-Span)
      const badge = screen.queryByText(String(erwartet));
      expect(badge).toBeInTheDocument();
    });
  });
});
