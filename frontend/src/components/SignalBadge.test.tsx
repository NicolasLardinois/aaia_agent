import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalBadge } from "./SignalBadge";

describe("SignalBadge", () => {
  it("zeigt das Signal-Wort", () => {
    render(<SignalBadge signal="bullish" />);
    expect(screen.getByText("BULLISH")).toBeInTheDocument();
  });
  it("zeigt bei null 'nicht verfuegbar'", () => {
    render(<SignalBadge signal={null} />);
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
  });
});
