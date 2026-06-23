import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestContextTab } from "./BacktestContextTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("BacktestContextTab", () => {
  it("zeigt Trefferquote, Stichprobe und Historie", () => {
    render(<BacktestContextTab ctx={demoDeepDive("AAPL").backtestContext!} />);
    expect(screen.getByText(/64/)).toBeInTheDocument();   // Trefferquote
    // Stichprobe 25 + Datum 2025-09 koennen beide /25/ matchen -> mind. 1 Element reicht
    expect(screen.getAllByText(/25/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/2025-09/)).toBeInTheDocument();
  });
});
