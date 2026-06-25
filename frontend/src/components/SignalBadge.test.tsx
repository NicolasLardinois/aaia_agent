import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SignalBadge } from "./SignalBadge";

describe("SignalBadge", () => {
  it("zeigt das Signal-Wort und die Farbklasse", () => {
    render(<SignalBadge signal="bullish" />);
    const el = screen.getByText("BULLISH");
    expect(el).toBeInTheDocument();
    // bullish nutzt den Finanz-Signal-Token (dark-mode-fähig), nicht mehr text-green-600
    expect(el).toHaveClass("text-bull");
  });
  it("zeigt bei null 'nicht verfuegbar' mit UNAVAILABLE-Farbe", () => {
    render(<SignalBadge signal={null} />);
    const el = screen.getByText("nicht verfügbar");
    expect(el).toBeInTheDocument();
    // UNAVAILABLE ist KEIN Signal -> text-muted, bewusst getrennt vom neutral-Signal-Token
    expect(el).toHaveClass("text-muted");
  });
});
