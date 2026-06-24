// BacktestFilters.test.tsx — TDD-Tests fuer die Filter-Steuerung (US32)
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BacktestFilters } from "./BacktestFilters";
import type { BacktestRegime } from "../../contract/backtest";

describe("BacktestFilters (US32)", () => {
  // regimes als typisierte Union (BacktestRegime[]) — spiegelt den verschaerften Prop-Typ.
  const defaultProps = {
    tickers: ["SPY", "AAPL"],
    underlyings: ["equity", "equity_index"],
    regimes: ["AUFSCHWUNG", "ABSCHWUNG"] as BacktestRegime[],
    horizons: [30, 60, 90],
    value: {},
    onChange: vi.fn(),
  };

  it("rendert alle vier Filter-Labels", () => {
    render(<BacktestFilters {...defaultProps} />);
    expect(screen.getByLabelText(/Ticker/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Asset-Klasse/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Regime/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Zeitfenster/i)).toBeInTheDocument();
  });

  it("Ticker-Auswahl meldet den Patch { ticker: 'AAPL' }", async () => {
    const onChange = vi.fn();
    render(<BacktestFilters {...defaultProps} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText(/Ticker/i), "AAPL");
    expect(onChange).toHaveBeenCalledWith({ ticker: "AAPL" });
  });

  it("Horizont-Auswahl meldet den Patch { horizon: 60 } als number", async () => {
    const onChange = vi.fn();
    render(<BacktestFilters {...defaultProps} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText(/Zeitfenster/i), "60");
    expect(onChange).toHaveBeenCalledWith({ horizon: 60 });
  });

  it("Alle-Option bei Asset-Klasse setzt die Achse zurueck (undefined)", async () => {
    const onChange = vi.fn();
    // Startzustand mit gesetztem Filter
    render(<BacktestFilters {...defaultProps} value={{ underlying: "equity" }} onChange={onChange} />);
    // "Alle" = leerer Wert -> underlying: undefined
    await userEvent.selectOptions(screen.getByLabelText(/Asset-Klasse/i), "");
    expect(onChange).toHaveBeenCalledWith({ underlying: undefined });
  });

  it("Alle-Option beim Ticker setzt die Achse zurueck (undefined)", async () => {
    const onChange = vi.fn();
    render(<BacktestFilters {...defaultProps} value={{ ticker: "SPY" }} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText(/Ticker/i), "");
    expect(onChange).toHaveBeenCalledWith({ ticker: undefined });
  });

  it("Regime-Auswahl meldet den Patch { regime: 'ABSCHWUNG' }", async () => {
    const onChange = vi.fn();
    render(<BacktestFilters {...defaultProps} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText(/Regime/i), "ABSCHWUNG");
    expect(onChange).toHaveBeenCalledWith({ regime: "ABSCHWUNG" });
  });

  it("Alle-Option beim Regime setzt die Achse zurueck (undefined)", async () => {
    const onChange = vi.fn();
    render(<BacktestFilters {...defaultProps} value={{ regime: "AUFSCHWUNG" }} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByLabelText(/Regime/i), "");
    expect(onChange).toHaveBeenCalledWith({ regime: undefined });
  });

  it("Alle Ticker-Optionen sind sichtbar (inkl. 'Alle')", () => {
    render(<BacktestFilters {...defaultProps} />);
    const select = screen.getByLabelText(/Ticker/i) as HTMLSelectElement;
    const optionValues = Array.from(select.options).map((o) => o.value);
    expect(optionValues).toContain("");       // "Alle"
    expect(optionValues).toContain("SPY");
    expect(optionValues).toContain("AAPL");
  });

  it("Alle Horizonte sind als '30 T / 60 T / 90 T' beschriftet", () => {
    render(<BacktestFilters {...defaultProps} />);
    expect(screen.getByText("30 T")).toBeInTheDocument();
    expect(screen.getByText("60 T")).toBeInTheDocument();
    expect(screen.getByText("90 T")).toBeInTheDocument();
  });
});
