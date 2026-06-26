import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  it("zeigt den Inbox-Badge mit Anzahl", () => {
    render(<MemoryRouter><Topbar inboxCount={3} onSearch={() => {}} /></MemoryRouter>);
    expect(screen.getByText("3")).toBeInTheDocument();
  });
  it("ruft onSearch mit dem eingegebenen Ticker", async () => {
    const onSearch = vi.fn();
    render(<MemoryRouter><Topbar inboxCount={0} onSearch={onSearch} /></MemoryRouter>);
    // Zugriff ueber den barrierefreien Namen (aria-label), nicht ueber den Placeholder
    // (Placeholder ist nur ein Beispiel-Hinweis, kein Label).
    await userEvent.type(screen.getByRole("combobox", { name: /suchen/i }), "AAPL{enter}");
    expect(onSearch).toHaveBeenCalledWith("AAPL");
  });

  it("löst einen Tippfehler bei Enter auf den richtigen Ticker auf (appl → AAPL)", async () => {
    const onSearch = vi.fn();
    render(<MemoryRouter><Topbar inboxCount={0} onSearch={onSearch} /></MemoryRouter>);
    await userEvent.type(screen.getByRole("combobox", { name: /suchen/i }), "appl{enter}");
    expect(onSearch).toHaveBeenCalledWith("AAPL");
  });

  it("zeigt Vorschläge während der Eingabe und navigiert per Klick", async () => {
    const onSearch = vi.fn();
    render(<MemoryRouter><Topbar inboxCount={0} onSearch={onSearch} /></MemoryRouter>);
    await userEvent.type(screen.getByRole("combobox", { name: /suchen/i }), "appl");
    const option = await screen.findByRole("option", { name: /AAPL/i });
    await userEvent.click(option);
    expect(onSearch).toHaveBeenCalledWith("AAPL");
  });

  it("findet über einen Synonym-Begriff: 'gold' schlägt eine Gold-Hülle vor", async () => {
    const onSearch = vi.fn();
    render(<MemoryRouter><Topbar inboxCount={0} onSearch={onSearch} /></MemoryRouter>);
    await userEvent.type(screen.getByRole("combobox", { name: /suchen/i }), "gold");
    // GC=F (Gold-Future) ist der erste Gold-Treffer (exakter Alias) und als Symbol eindeutig.
    expect(await screen.findByRole("option", { name: /GC=F/i })).toBeInTheDocument();
  });
});
