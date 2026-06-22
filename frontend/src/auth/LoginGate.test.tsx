import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LoginGate } from "./LoginGate";

describe("LoginGate", () => {
  it("ruft onSubmit mit dem eingegebenen Passwort", () => {
    const onSubmit = vi.fn();
    render(<LoginGate onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText("Passwort"), { target: { value: "geheim" } });
    fireEvent.click(screen.getByRole("button", { name: /Anmelden/i }));
    expect(onSubmit).toHaveBeenCalledWith("geheim");
  });

  it("zeigt bei error die Meldung 'Falsches Passwort'", () => {
    render(<LoginGate error onSubmit={() => {}} />);
    expect(screen.getByText(/Falsches Passwort/i)).toBeInTheDocument();
  });
});
