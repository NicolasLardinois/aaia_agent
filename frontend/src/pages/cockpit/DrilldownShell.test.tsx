import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DrilldownShell } from "./DrilldownShell";

function renderShell(props: Parameters<typeof DrilldownShell>[0]) {
  return render(
    <MemoryRouter>
      <DrilldownShell {...props} />
    </MemoryRouter>,
  );
}

const demoView = {
  isDemo: true,
  sourcesActive: 2,
  sourcesTotal: 3,
  failed: [{ key: "Quelle-A", reason: "Timeout" }],
};

describe("DrilldownShell", () => {
  it("rendert Titel und Zurück-Link", () => {
    renderShell({ title: "Makro", view: demoView, loading: false, error: null, children: <p>Inhalt</p> });
    expect(screen.getByText("Makro")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /zurück/i });
    expect(link).toHaveAttribute("href", "/cockpit");
  });

  it("zeigt Demo-Badge wenn isDemo=true", () => {
    renderShell({ title: "Test", view: demoView, loading: false, error: null, children: null });
    expect(screen.getByText("Demo-Daten")).toBeInTheDocument();
  });

  it("zeigt kein Demo-Badge wenn isDemo=false", () => {
    const liveView = { ...demoView, isDemo: false };
    renderShell({ title: "Test", view: liveView, loading: false, error: null, children: null });
    expect(screen.queryByText("Demo-Daten")).not.toBeInTheDocument();
  });

  it("zeigt SourceHealth mit failed-Warnung", () => {
    renderShell({ title: "Test", view: demoView, loading: false, error: null, children: null });
    expect(screen.getByText("2/3 Quellen aktiv")).toBeInTheDocument();
    expect(screen.getByLabelText("Quellen ausgefallen")).toBeInTheDocument();
  });

  it("zeigt Lädt… bei loading=true, keine children", () => {
    renderShell({ title: "Test", view: null, loading: true, error: null, children: <p>Inhalt</p> });
    expect(screen.getByText("Lädt …")).toBeInTheDocument();
    expect(screen.queryByText("Inhalt")).not.toBeInTheDocument();
  });

  it("zeigt Fehlertext bei error, keine children", () => {
    renderShell({ title: "Test", view: null, loading: false, error: "Verbindung fehlgeschlagen", children: <p>Inhalt</p> });
    expect(screen.getByText("Verbindung fehlgeschlagen")).toBeInTheDocument();
    expect(screen.queryByText("Inhalt")).not.toBeInTheDocument();
  });

  it("rendert children bei erfolgreich geladenem view", () => {
    renderShell({ title: "Test", view: demoView, loading: false, error: null, children: <p>Mein Inhalt</p> });
    expect(screen.getByText("Mein Inhalt")).toBeInTheDocument();
  });
});
