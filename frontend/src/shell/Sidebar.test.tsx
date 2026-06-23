import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("zeigt alle fuenf Hauptbereiche + Einstellungen", () => {
    render(<MemoryRouter><Sidebar /></MemoryRouter>);
    for (const label of ["Cockpit", "Deep-Dive", "Portfolio", "Inbox", "Backtester", "Einstellungen"]) {
      expect(screen.getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });
});
