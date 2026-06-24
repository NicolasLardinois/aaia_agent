import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CockpitPage } from "./CockpitPage";
import type { WebSocketLike } from "../api/cockpitSocket";

function fakeFetch(status: number, body?: unknown): typeof fetch {
  return (async () => ({ status, ok: status >= 200 && status < 300, json: async () => body })) as unknown as typeof fetch;
}
const fakeWs = (): WebSocketLike => ({ onopen: null, onmessage: null, onerror: null, onclose: null, close: vi.fn() });

// DomainTile verwendet jetzt Link -> CockpitPage braucht Router-Kontext.
function renderCockpit(deps: Parameters<typeof CockpitPage>[0]["deps"]) {
  return render(
    <MemoryRouter>
      <CockpitPage deps={deps} />
    </MemoryRouter>,
  );
}

const overview = {
  regime: "Aufschwung", regime_confidence: 0.71, macro_status: "available",
  domains: [
    { key: "commodities", signal: "neutral", status: "available" },
    { key: "sentiment", signal: "bearish", status: "available" },
    { key: "yield_curve", signal: "bullish", status: "available" },
    { key: "sectors", signal: null, status: "unavailable" },
  ],
  sources_active: 4, sources_total: 5,
};

describe("CockpitPage", () => {
  it("zeigt Regime, vier Kacheln und den Health-Zaehler bei 200", async () => {
    renderCockpit({ base: "http://x", fetchFn: fakeFetch(200, overview), wsFactory: fakeWs });
    await waitFor(() => expect(screen.getByText("Aufschwung")).toBeInTheDocument());
    expect(screen.getByText("71 %")).toBeInTheDocument();
    expect(screen.getByText("BEARISH")).toBeInTheDocument();
    expect(screen.getByText("4/5 Quellen aktiv")).toBeInTheDocument();
    // Seitenspezifischer Titel (globaler Header jetzt in Topbar)
    expect(screen.getByText("Cockpit — Übersicht")).toBeInTheDocument();
    // ausgefallene Sektoren-Domaene: kein Signal, sondern 'nicht verfuegbar'
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
  });

  it("zeigt den Leerzustand bei 204", async () => {
    renderCockpit({ base: "http://x", fetchFn: fakeFetch(204), wsFactory: fakeWs });
    await waitFor(() => expect(screen.getByText(/Noch keine Analyse/i)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Analyse starten/i })).toBeInTheDocument();
  });

  it("zeigt einen Fehlerhinweis, wenn das Backend nicht erreichbar ist", async () => {
    renderCockpit({ base: "http://x", fetchFn: fakeFetch(500), wsFactory: fakeWs });
    await waitFor(() => expect(screen.getByText(/nicht erreichbar/i)).toBeInTheDocument());
  });

  it("zeigt waehrend eines laufenden Laufs keinen Leerzustand mehr", async () => {
    const ws = fakeWs();
    renderCockpit({ base: "http://x", fetchFn: fakeFetch(204), wsFactory: () => ws });
    await waitFor(() => expect(screen.getByText(/Noch keine Analyse/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Analyse starten/i }));
    expect(screen.queryByText(/Noch keine Analyse/i)).not.toBeInTheDocument();
    expect(screen.getByText("läuft …")).toBeInTheDocument();
  });
});
