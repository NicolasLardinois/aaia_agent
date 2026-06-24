import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BacktestContextTab } from "./BacktestContextTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

describe("BacktestContextTab", () => {
  it("zeigt Trefferquote, Stichprobe und Historie", () => {
    render(<BacktestContextTab ctx={demoDeepDive("AAPL").backtestContext!} />);
    expect(screen.getByText(/64/)).toBeInTheDocument();   // Trefferquote
    // Stichprobe: exakte Prüfung "25 historische Calls"
    expect(screen.getByText(/25 historische Calls/)).toBeInTheDocument();
    expect(screen.getByText(/2025-09/)).toBeInTheDocument();
  });
});
