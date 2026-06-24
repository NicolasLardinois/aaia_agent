import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./routes";

// Cockpit-Datenhook neutralisieren (kein echter Netz-Call im Routing-Test).
vi.mock("./hooks/useCockpit", () => ({
  useCockpit: () => ({ overview: null, phase: "ready", error: null, events: [], startAnalysis: () => {} }),
}));

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>);
}

describe("AppRoutes", () => {
  it("zeigt Portfolio-Platzhalter unter /portfolio", () => {
    renderAt("/portfolio");
    // Platzhalter-Seite zeigt Überschrift + Hinweis
    expect(screen.getByRole("heading", { name: /Portfolio/i })).toBeInTheDocument();
    expect(screen.getByText(/in einem folgenden Slice/i)).toBeInTheDocument();
  });
  it("leitet / auf das Cockpit", () => {
    renderAt("/");
    // Nach Redirect: Cockpit-Übersichtsseite sichtbar
    expect(screen.getByRole("heading", { name: /Cockpit — Übersicht/i })).toBeInTheDocument();
  });
});
