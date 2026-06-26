import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route, Link } from "react-router-dom";
import { CockpitProvider } from "./CockpitProvider";
import { CockpitPage } from "../pages/CockpitPage";
import type { WebSocketLike } from "../api/cockpitSocket";

// Regression fuer Bug #5/#7: Ein laufender Cockpit-Lauf darf NICHT abbrechen, nur
// weil der Nutzer waehrenddessen auf eine andere Route wechselt (Portfolio, Buffett,
// Big-Mac …). Frueher hing der Lauf-Zustand (WebSocket + phase) an der CockpitPage;
// beim Wegnavigieren wurde die Seite ausgehaengt und der Socket geschlossen.
// Mit dem CockpitProvider lebt der Zustand OBERHALB der Routen -> er ueberlebt.

const fakeFetch = (status: number, body?: unknown): typeof fetch =>
  (async () => ({ status, ok: status >= 200 && status < 300, json: async () => body })) as unknown as typeof fetch;

function fakeWs(): WebSocketLike {
  return { onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() };
}

function PortfolioStub() {
  return <p>Portfolio-Seite</p>;
}

function renderApp(ws: WebSocketLike) {
  return render(
    <MemoryRouter initialEntries={["/cockpit"]}>
      <CockpitProvider deps={{ base: "http://x", fetchFn: fakeFetch(204), wsFactory: () => ws }}>
        <nav>
          <Link to="/cockpit">Zum Cockpit</Link>
          <Link to="/portfolio">Zum Portfolio</Link>
        </nav>
        <Routes>
          <Route path="/cockpit" element={<CockpitPage />} />
          <Route path="/portfolio" element={<PortfolioStub />} />
        </Routes>
      </CockpitProvider>
    </MemoryRouter>,
  );
}

describe("CockpitProvider — Lauf ueberlebt Navigation (Bug #5/#7)", () => {
  it("schliesst den WebSocket NICHT, wenn waehrend des Laufs die Route wechselt", async () => {
    const ws = fakeWs();
    renderApp(ws);
    await waitFor(() => expect(screen.getByRole("button", { name: /Analyse starten/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Analyse starten/i }));
    expect(screen.getByText("läuft …")).toBeInTheDocument();

    // Waehrend des Laufs auf eine andere Seite navigieren.
    fireEvent.click(screen.getByText("Zum Portfolio"));
    expect(screen.getByText("Portfolio-Seite")).toBeInTheDocument();
    // Der Bug: hier wurde der Socket frueher geschlossen (Analyse brach ab).
    expect(ws.close).not.toHaveBeenCalled();
  });

  it("zeigt den laufenden Lauf nach der Rueckkehr ins Cockpit weiterhin an", async () => {
    const ws = fakeWs();
    renderApp(ws);
    await waitFor(() => expect(screen.getByRole("button", { name: /Analyse starten/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Analyse starten/i }));
    fireEvent.click(screen.getByText("Zum Portfolio"));
    expect(screen.queryByText("läuft …")).not.toBeInTheDocument(); // Cockpit ist ausgehaengt …

    fireEvent.click(screen.getByText("Zum Cockpit"));
    // … aber der Lauf-Zustand lebt im Provider weiter -> nach Rueckkehr wieder sichtbar.
    expect(screen.getByText("läuft …")).toBeInTheDocument();
    expect(ws.close).not.toHaveBeenCalled();
  });
});
