import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutoHoldBadge, CashBiasBadge } from "./ThresholdBadges";

describe("Schwellen-Badges", () => {
  it("AutoHoldBadge erscheint unter 0.50, nicht darueber", () => {
    const { rerender, container } = render(<AutoHoldBadge confidence={0.49} />);
    expect(screen.getByText(/auto-HOLD/i)).toBeInTheDocument();
    rerender(<AutoHoldBadge confidence={0.6} />);
    expect(container).toBeEmptyDOMElement();
  });
  it("CashBiasBadge erscheint unter 0.35", () => {
    render(<CashBiasBadge confidence={0.30} />);
    expect(screen.getByText(/Cash-Bias/i)).toBeInTheDocument();
  });
});
