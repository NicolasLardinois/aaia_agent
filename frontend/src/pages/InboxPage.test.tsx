// InboxPage.test.tsx
// TDD Rot-Phase: Tests fuer InboxPage (US28/US30).
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { InboxPage } from "./InboxPage";
import { demoInbox } from "../data/demo/inbox";

// Steuerbarer Loader: gibt die Demo-Inbox synchron zurueck (Promise.resolve).
const demoLoader = () => Promise.resolve(demoInbox());

function renderInbox(loader = demoLoader) {
  return render(
    <MemoryRouter>
      <InboxPage loader={loader} />
    </MemoryRouter>,
  );
}

describe("InboxPage (US28/US30)", () => {
  it("zeigt die Ueberschrift 'Konflikt-Inbox'", async () => {
    renderInbox();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Konflikt-Inbox/i })).toBeInTheDocument(),
    );
  });

  it("zeigt zwei Tabs: Offen und Erledigt", async () => {
    renderInbox();
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /Offen/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /Erledigt/i })).toBeInTheDocument();
    });
  });

  it("Offen-Tab ist initial aktiv und zeigt die Konflikte", async () => {
    renderInbox();
    // XLE ist der erste Demo-Konflikt
    await screen.findByText("XLE");
    const offenTab = screen.getByRole("tab", { name: /Offen/i });
    expect(offenTab).toHaveAttribute("aria-selected", "true");
  });

  it("zeigt DemoBadge (isDemo=true in der Demo-Inbox)", async () => {
    renderInbox();
    await waitFor(() =>
      expect(screen.getByText("Demo-Daten")).toBeInTheDocument(),
    );
  });

  it("Abarbeiten (Gefolgt) verschiebt XLE von Offen nach Erledigt", async () => {
    renderInbox();
    // Warten bis XLE sichtbar ist
    await screen.findByText("XLE");

    // Klick auf "Gefolgt" bei der XLE-Karte
    const gefolgButtons = screen.getAllByRole("button", { name: /Gefolgt/i });
    await userEvent.click(gefolgButtons[0]);

    // XLE sollte jetzt nicht mehr im Offen-Tab sein (als Conflict-Karte mit onResolve)
    // Offen-Tab: Tab-Zaehler muss um 1 gesunken sein
    // Wechsel auf Erledigt-Tab
    const erledigtTab = screen.getByRole("tab", { name: /Erledigt/i });
    await userEvent.click(erledigtTab);

    // Im Erledigt-Tab: XLE mit Audit-Label "Erledigt: gefolgt" sichtbar
    await waitFor(() =>
      expect(screen.getByText(/Erledigt: gefolgt/i)).toBeInTheDocument(),
    );
  });

  it("nach Abarbeiten: Offen-Zaehler sinkt um 1", async () => {
    renderInbox();
    await screen.findByText("XLE");

    // Zuerst offene Anzahl merken
    const offenTab = screen.getByRole("tab", { name: /Offen/i });
    const initText = offenTab.textContent ?? "";
    // Zaehler befindet sich im Tab-Text, z.B. "Offen (3)"
    const match = initText.match(/\((\d+)\)/);
    const initCount = match ? parseInt(match[1]) : 0;
    expect(initCount).toBeGreaterThanOrEqual(1);

    // Klick auf Gefolgt
    const gefolgButtons = screen.getAllByRole("button", { name: /Gefolgt/i });
    await userEvent.click(gefolgButtons[0]);

    // Neuer Tab-Text: Zaehler muss um 1 kleiner sein
    await waitFor(() => {
      const newText = screen.getByRole("tab", { name: /Offen/i }).textContent ?? "";
      const newMatch = newText.match(/\((\d+)\)/);
      const newCount = newMatch ? parseInt(newMatch[1]) : 0;
      expect(newCount).toBe(initCount - 1);
    });
  });

  it("sind alle Konflikte erledigt: Offen-Tab zeigt 'Keine offenen Konflikte.'", async () => {
    // Loader mit nur einem Konflikt fuer schnelle Erledigung
    const singleConflict = demoInbox();
    const [first] = singleConflict.conflicts;
    const singleLoader = () =>
      Promise.resolve({ ...singleConflict, conflicts: [first] });

    renderInbox(singleLoader);
    await screen.findByText(first.ticker);

    await userEvent.click(screen.getByRole("button", { name: /Gefolgt/i }));

    await waitFor(() =>
      expect(screen.getByText(/Keine offenen Konflikte\./i)).toBeInTheDocument(),
    );
  });

  it("zeigt 'Lädt …' waehrend des Ladens", () => {
    // Loader, der nie auflöst (haengt) -> loading:true
    const hangingLoader = () => new Promise<never>(() => {});
    renderInbox(hangingLoader);
    expect(screen.getByText(/Lädt/)).toBeInTheDocument();
  });

  it("zeigt Fehlertext wenn der Loader rejected", async () => {
    const errorLoader = () => Promise.reject(new Error("Testfehler"));
    renderInbox(errorLoader);
    await waitFor(() => expect(screen.getByText(/Fehler/i)).toBeInTheDocument());
  });
});
