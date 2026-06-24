import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("rendert die Shell + den Outlet-Inhalt der aktiven Route", () => {
    render(
      <MemoryRouter initialEntries={["/cockpit"]}>
        <Routes>
          <Route element={<AppShell inboxCount={0} />}>
            <Route path="/cockpit" element={<div>COCKPIT-INHALT</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("COCKPIT-INHALT")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Portfolio/i })).toBeInTheDocument();
  });
});
