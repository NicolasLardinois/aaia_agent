import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SectionCard } from "./SectionCard";

describe("SectionCard", () => {
  it("rendert Titel, Untertitel und Inhalt", () => {
    render(
      <SectionCard title="Makro" subtitle="Großwetterlage">
        <p>Inhalt</p>
      </SectionCard>,
    );
    expect(screen.getByRole("heading", { name: "Makro" })).toBeInTheDocument();
    expect(screen.getByText("Großwetterlage")).toBeInTheDocument();
    expect(screen.getByText("Inhalt")).toBeInTheDocument();
  });
});
