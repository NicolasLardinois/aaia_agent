import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { UnavailableField } from "./UnavailableField";

describe("UnavailableField", () => {
  it("zeigt 'nicht verfuegbar' und den Grund als Titel", () => {
    render(<UnavailableField reason="Stub-Quelle" />);
    const el = screen.getByText("nicht verfügbar");
    expect(el).toBeInTheDocument();
    expect(screen.getByTitle("Stub-Quelle")).toBeInTheDocument();
  });
});
