import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { WelcomePage } from "./WelcomePage";

function renderWelcome() {
  return render(
    <MemoryRouter initialEntries={["/willkommen"]}>
      <Routes>
        <Route path="/willkommen" element={<WelcomePage />} />
        <Route path="/cockpit" element={<h1>Cockpit-Ziel</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());

describe("WelcomePage", () => {
  it("erklärt jeden der fünf Bereiche mit Link", () => {
    renderWelcome();
    for (const [name, to] of [
      ["Cockpit", "/cockpit"], ["Deep-Dive", "/deep-dive"], ["Portfolio", "/portfolio"],
      ["Inbox", "/inbox"], ["Backtester", "/backtester"],
    ] as const) {
      const link = screen.getByRole("link", { name: new RegExp(name, "i") });
      expect(link).toHaveAttribute("href", to);
    }
  });
  it("setzt das gesehen-Flag und navigiert ins Cockpit beim 'los geht's'-Knopf", async () => {
    renderWelcome();
    await userEvent.click(screen.getByRole("button", { name: /los geht's/i }));
    expect(localStorage.getItem("aaia_onboarding_seen")).toBe("1");
    expect(screen.getByRole("heading", { name: "Cockpit-Ziel" })).toBeInTheDocument();
  });
});
