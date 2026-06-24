import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HedgeSuggestions } from "./HedgeSuggestions";
import type { HedgeSuggestionDTO } from "../../contract/portfolio";

const h: HedgeSuggestionDTO = {
  id: "net-beta", text: "net_beta 62 % senken → Index-Short (z. B. SPY) oder VIX-Hedge erwägen",
  rationale: "aktien-only net_beta über 30 % NAV — Buch ist marktsensitiv",
};

describe("HedgeSuggestions", () => {
  it("zeigt den Vorschlag und den beratend-Hinweis (keine Ausführung)", () => {
    render(<HedgeSuggestions hedges={[h]} />);
    expect(screen.getByText(/Index-Short/)).toBeInTheDocument();
    expect(screen.getByText(/beratend, keine Ausführung/i)).toBeInTheDocument();
  });
  it("hat KEINEN Ausführungs-Button (US27)", () => {
    render(<HedgeSuggestions hedges={[h]} />);
    expect(screen.queryByRole("button")).toBeNull();
  });
  it("leere Liste => Entwarnung", () => {
    render(<HedgeSuggestions hedges={[]} />);
    expect(screen.getByText(/kein Hedge nötig/i)).toBeInTheDocument();
  });
});
