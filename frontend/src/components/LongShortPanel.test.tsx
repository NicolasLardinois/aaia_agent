import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LongShortPanel } from "./LongShortPanel";

describe("LongShortPanel", () => {
  it("zeigt beide Linsen gleichwertig nebeneinander + Konfidenz-%", () => {
    render(
      <LongShortPanel
        long={{ verdict: "HOLD", confidence: 0.47, rationale: "Roll-Gegenwind" }}
        short={{ verdict: "NONE", confidence: 0.22, rationale: "kein Short" }}
      />,
    );
    expect(screen.getByText("LONG-LINSE")).toBeInTheDocument();
    expect(screen.getByText("SHORT-LINSE")).toBeInTheDocument();
    expect(screen.getByText("47 %")).toBeInTheDocument();
    expect(screen.getByText("22 %")).toBeInTheDocument();
  });
  it("zeigt das auto-HOLD-Flag unter 0.50", () => {
    render(
      <LongShortPanel
        long={{ verdict: "HOLD", confidence: 0.47, rationale: "x" }}
        short={{ verdict: "NONE", confidence: 0.22, rationale: "y" }}
      />,
    );
    // Beide Linsen haben confidence < 0.50 -> beide zeigen AutoHold (Long: 0.47, Short: 0.22)
    expect(screen.getAllByText(/auto-HOLD/i)).toHaveLength(2);
  });
});
