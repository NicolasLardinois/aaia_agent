import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricRow } from "./MetricRow";

describe("MetricRow", () => {
  it("zeigt Label, Wert und Einheit", () => {
    render(<MetricRow label="KGV" value={30.5} unit="x" />);
    expect(screen.getByText("KGV")).toBeInTheDocument();
    expect(screen.getByText("30.5 x")).toBeInTheDocument();
  });
  it("zeigt 'n.v.' statt eines Wertes, wenn value null ist (UNAVAILABLE ≠ 0)", () => {
    render(<MetricRow label="Earnings-Trend" value={null} />);
    expect(screen.getByText("n.v.")).toBeInTheDocument();
  });
  it("bindet einen InfoTip ein, wenn ein Begriff gesetzt ist", () => {
    render(<MetricRow label="Exposure" value={120} unit="%" term="Exposure" />);
    expect(screen.getByRole("button", { name: /Erklärung: Exposure/i })).toBeInTheDocument();
  });
});
