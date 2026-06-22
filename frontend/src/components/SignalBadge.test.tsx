import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalBadge } from "./SignalBadge";

describe("SignalBadge", () => {
  it("zeigt das Signal-Wort und die Farbklasse", () => {
    render(<SignalBadge signal="bullish" />);
    const el = screen.getByText("BULLISH");
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass("text-green-600");
  });
  it("zeigt bei null 'nicht verfuegbar' mit UNAVAILABLE-Farbe", () => {
    render(<SignalBadge signal={null} />);
    const el = screen.getByText("nicht verfügbar");
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass("text-slate-400");
  });
});
