import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FuturesTab } from "./FuturesTab";
import { demoDeepDive } from "../../../data/demo/deepdive";

vi.mock("echarts-for-react", () => ({ default: () => null }));

describe("FuturesTab", () => {
  it("GC=F: Contango, negativer Roll-Yield (Gegenwind), Verfall/Roll, Hebel ~33x", () => {
    render(<FuturesTab block={demoDeepDive("GC=F").futures!} />);
    // form "contango" als uppercase-Span sichtbar
    expect(screen.getByText("contango", { selector: ".font-medium.uppercase" })).toBeInTheDocument();
    // Roll-Yield: -3.1 %/Jahr im Roll-Yield-Abschnitt
    expect(screen.getByText(/-3\.1/)).toBeInTheDocument();
    // rollYieldVisual-Label: Gegenwind (Contango)
    expect(screen.getByText(/Gegenwind/i)).toBeInTheDocument();
    // Verfall und Roll-Datum
    expect(screen.getAllByText(/2026-06-26/).length).toBeGreaterThanOrEqual(1);
    // Hebel ≈ 33x (238000 / 7150 ≈ 33.3)
    expect(screen.getByText(/33/)).toBeInTheDocument();
  });
});
