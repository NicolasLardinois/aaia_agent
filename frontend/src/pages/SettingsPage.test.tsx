import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { SettingsPage } from "./SettingsPage";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("dark");
  delete document.documentElement.dataset.reduceMotion;
});

function renderPage(onLogout?: () => void) {
  return render(
    <MemoryRouter initialEntries={["/einstellungen"]}>
      <Routes>
        <Route path="/einstellungen" element={<SettingsPage onLogout={onLogout} />} />
        <Route path="/willkommen" element={<div>WILLKOMMEN-SEITE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SettingsPage", () => {
  it("zeigt die echten Einstellungs-Gruppen (kein Platzhalter mehr)", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /Erscheinungsbild/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Bewegung/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Start-Ansicht/i })).toBeInTheDocument();
  });

  it("schaltet auf Dunkel und setzt die 'dark'-Klasse + persistiert", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("radio", { name: "Dunkel" }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("aaia_theme")).toBe("dark");
  });

  it("erzwingt reduzierte Bewegung und persistiert", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("radio", { name: "Reduzieren" }));
    expect(document.documentElement.dataset.reduceMotion).toBe("reduce");
    expect(localStorage.getItem("aaia_motion")).toBe("reduce");
  });

  it("merkt sich die gewählte Start-Ansicht", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("radio", { name: "Portfolio" }));
    expect(localStorage.getItem("aaia_start_view")).toBe("/portfolio");
  });

  it("zeigt die Einführung erneut an (setzt Onboarding zurück und navigiert)", async () => {
    localStorage.setItem("aaia_onboarding_seen", "1");
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: /Einführung erneut anzeigen/i }));
    expect(await screen.findByText("WILLKOMMEN-SEITE")).toBeInTheDocument();
    expect(localStorage.getItem("aaia_onboarding_seen")).toBeNull();
  });

  it("ruft onLogout beim Abmelden auf — und blendet den Knopf ohne Handler aus", async () => {
    const onLogout = vi.fn();
    const { unmount } = renderPage(onLogout);
    await userEvent.click(screen.getByRole("button", { name: /Abmelden/i }));
    expect(onLogout).toHaveBeenCalledTimes(1);
    unmount();

    renderPage(); // ohne Handler
    expect(screen.queryByRole("button", { name: /Abmelden/i })).toBeNull();
  });
});
