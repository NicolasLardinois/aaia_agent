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
    await userEvent.type(screen.getByPlaceholderText(/Ticker/i), "AAPL{enter}");
    expect(onSearch).toHaveBeenCalledWith("AAPL");
  });
});
