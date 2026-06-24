// BacktestCard.test.tsx — TDD-Tests fuer die Backtester-Karten-Komponente (US31)
// ECharts im jsdom neutralisieren — kein Canvas-Renderer verfuegbar.
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestCard } from "./BacktestCard";
import type { BacktestResult } from "../../contract/backtest";

vi.mock("echarts-for-react", () => ({ default: () => null }));
vi.mock("echarts", () => ({ registerMap: vi.fn() }));

// Zwei Test-Ergebnisse: ein korrekter, ein falscher Call.
const CORRECT: BacktestResult = {
  id: "t1", area: "top_down", ticker: "SPY", underlying: "equity_index",
  regime: "AUFSCHWUNG", horizon: 30, correct: true, timestamp: "2026-01-01",
};
const WRONG: BacktestResult = {
  id: "t2", area: "top_down", ticker: "SPY", underlying: "equity_index",
  regime: "ABSCHWUNG", horizon: 60, correct: false, timestamp: "2026-02-01",
};

describe("BacktestCard (US31)", () => {
  it("rendert den Bereichs-Titel fuer top_down", () => {
    render(<BacktestCard area="top_down" results={[CORRECT, WRONG]} />);
    expect(screen.getByText(/Top-Down/i)).toBeInTheDocument();
  });

  it("zeigt die Trefferquote (50 % bei 1 von 2 korrekt)", () => {
    render(<BacktestCard area="top_down" results={[CORRECT, WRONG]} />);
    expect(screen.getByText("50 %")).toBeInTheDocument();
  });

  it("zeigt die Stichprobengroesse n = 2", () => {
    render(<BacktestCard area="top_down" results={[CORRECT, WRONG]} />);
    expect(screen.getByText(/n = 2/)).toBeInTheDocument();
  });

  it("zeigt die 'haetten die alten Calls Geld gebracht'-Beschriftung", () => {
    render(<BacktestCard area="top_down" results={[CORRECT, WRONG]} />);
    expect(screen.getByText(/Geld gebracht/i)).toBeInTheDocument();
  });

  it("n.v.-Pfad: leere Ergebnisse -> 'n.v.' anzeigen, NICHT '0 %'", () => {
    render(<BacktestCard area="judgment" results={[]} />);
    expect(screen.getByText("n.v.")).toBeInTheDocument();
    expect(screen.queryByText("0 %")).toBeNull();
  });

  it("n.v.-Pfad: leere Ergebnisse -> Hinweis 'Keine Daten' (kein Chart)", () => {
    render(<BacktestCard area="judgment" results={[]} />);
    expect(screen.getByText(/Keine Daten/i)).toBeInTheDocument();
  });

  it("n.v.-Pfad: Stichprobengroesse n = 0 sichtbar", () => {
    render(<BacktestCard area="bottom_up" results={[]} />);
    expect(screen.getByText(/n = 0/)).toBeInTheDocument();
  });

  it("Titel fuer bottom_up-Bereich korrekt", () => {
    render(<BacktestCard area="bottom_up" results={[CORRECT]} />);
    expect(screen.getByText(/Bottom-Up/i)).toBeInTheDocument();
  });

  it("Titel fuer judgment-Bereich korrekt", () => {
    render(<BacktestCard area="judgment" results={[CORRECT]} />);
    expect(screen.getByText(/Judgment/i)).toBeInTheDocument();
  });
});
