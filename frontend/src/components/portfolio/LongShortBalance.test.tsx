import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LongShortBalance } from "./LongShortBalance";

describe("LongShortBalance", () => {
  it("zeigt Long-/Short-Brutto mit Anzahl und die Netto-Richtung", () => {
    render(<LongShortBalance split={{
      grossLongPct: 52, grossShortPct: 5, netPct: 47, longCount: 5, shortCount: 1,
    }} />);
    expect(screen.getByText(/Long 52 % · 5/)).toBeInTheDocument();
    expect(screen.getByText(/Short 5 % · 1/)).toBeInTheDocument();
    // Netto positiv -> mit Vorzeichen
    expect(screen.getByText(/\+47 %/)).toBeInTheDocument();
    // Balken ist als Bild mit sprechendem aria-label ausgezeichnet
    expect(screen.getByRole("img", { name: /Long 52 Prozent, Short 5 Prozent, Netto \+47 Prozent/ })).toBeInTheDocument();
  });

  it("stellt eine negative Netto-Richtung mit Minus dar", () => {
    render(<LongShortBalance split={{
      grossLongPct: 10, grossShortPct: 30, netPct: -20, longCount: 1, shortCount: 2,
    }} />);
    expect(screen.getByText(/−20 %|−20 Prozent|-20 %/)).toBeTruthy();
    expect(screen.getByRole("img", { name: /Netto -20 Prozent/ })).toBeInTheDocument();
  });
});
