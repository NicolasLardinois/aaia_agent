import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBar } from "./ConfidenceBar";

describe("ConfidenceBar", () => {
  it("zeigt das Prozent-Label", () => {
    render(<ConfidenceBar value={0.71} />);
    expect(screen.getByText("71 %")).toBeInTheDocument();
  });
  it("setzt die Balkenbreite per aria-Wert", () => {
    render(<ConfidenceBar value={0.71} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "71");
  });
});
