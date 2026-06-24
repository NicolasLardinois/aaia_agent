// BacktesterPage.test.tsx — TDD-Tests fuer die Backtester-Seite (US31/US32)
// ECharts neutralisieren (kein Canvas im jsdom).
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { BacktesterPage } from "./BacktesterPage";
import { demoBacktest } from "../data/demo/backtest";

vi.mock("echarts-for-react", () => ({ default: () => null }));
vi.mock("echarts", () => ({ registerMap: vi.fn() }));

// Stabiler Loader mit Demo-Fixture — kein Refetch-Loop (Modul-Identitaet).
const stableLoader = () => Promise.resolve(demoBacktest());

function renderPage() {
  return render(
    <MemoryRouter>
      <BacktesterPage loader={stableLoader} />
    </MemoryRouter>,
  );
}

describe("BacktesterPage (US31/US32)", () => {
  it("zeigt alle drei Bereichs-Karten (Top-Down/Bottom-Up/Judgment)", async () => {
    renderPage();
    await screen.findByText(/Top-Down/i);
    await screen.findByText(/Bottom-Up/i);
    await screen.findByText(/Judgment/i);
  });

  it("zeigt DemoBadge (Fixture isDemo:true)", async () => {
    renderPage();
    // DemoBadge zeigt "Demo-Daten" wenn isDemo:true
    await screen.findByText(/Demo-Daten/i);
  });

  it("zeigt SourceHealth mit der ausgefallenen Quelle (2/3 aktiv)", async () => {
    renderPage();
    // SourceHealth: sourcesActive=2, sourcesTotal=3 -> "2/3 Quellen aktiv"
    await screen.findByText(/2\/3 Quellen aktiv/i);
  });

  it("'haetten die alten Calls Geld gebracht'-Beschriftung auf allen Karten", async () => {
    renderPage();
    await screen.findByText(/Top-Down/i);
    // Alle drei Karten tragen die Pflicht-Beschriftung (US31) — 3 Karten + 1 Seitentitel = 4x vorhanden
    expect(screen.getAllByText(/Geld gebracht/i)).toHaveLength(4);
  });

  it("Filter nach Ticker 'XLE' (nur in judgment) -> zwei Karten zeigen 'n.v.'", async () => {
    renderPage();
    await screen.findByText(/Top-Down/i);

    // XLE ist nur im judgment-Bereich (ju-2) -> top_down + bottom_up werden leer -> n.v.
    const tickerSelect = screen.getByLabelText(/Ticker/i);
    await userEvent.selectOptions(tickerSelect, "XLE");

    // Mindestens 2 Karten zeigen "n.v." (leere Stichprobe nach Filter)
    await waitFor(() => {
      const nvMatches = screen.getAllByText("n.v.");
      expect(nvMatches.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("Ladetext erscheint kurz waehrend dem Laden", () => {
    // Langsamer Loader zum Pruefen des Lade-Zustands
    const slowLoader = () => new Promise<ReturnType<typeof demoBacktest>>(() => {/* pending */});
    render(<MemoryRouter><BacktesterPage loader={slowLoader} /></MemoryRouter>);
    expect(screen.getByText(/Lädt/i)).toBeInTheDocument();
  });
});
