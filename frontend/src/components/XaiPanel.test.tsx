import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { XaiPanel } from "./XaiPanel";

const xai = {
  drivers: [{ text: "Makro stützt", sign: "+" as const }, { text: "Contango bremst", sign: "-" as const }],
  conflicts: ["Top-Down bullish vs. Roll-Struktur bearish"],
  confidenceReason: "2 starke Gegensignale + 1 Quelle UNAVAILABLE",
  whatFlips: "Wechsel in Backwardation ODER Realzins ↓",
};

describe("XaiPanel", () => {
  it("zeigt nach dem Aufklappen Treiber, Widersprueche und 'was kippt'", async () => {
    render(<XaiPanel xai={xai} />);
    await userEvent.click(screen.getByRole("button", { name: /XAI/i }));
    expect(screen.getByText(/Makro stützt/)).toBeInTheDocument();
    expect(screen.getByText(/Top-Down bullish/)).toBeInTheDocument();
    expect(screen.getByText(/Backwardation/)).toBeInTheDocument();
  });
});
