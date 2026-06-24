import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CockpitWind } from "./CockpitWind";

describe("CockpitWind", () => {
  it("zeigt Domänen-Label, Note und einen Link ins Drilldown", () => {
    render(
      <MemoryRouter>
        <CockpitWind wind={{ domainKey: "commodities", domainLabel: "Rohstoffe (Öl)", signal: "bullish", note: "Öl stützt." }} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Rohstoffe \(Öl\)/)).toBeInTheDocument();
    expect(screen.getByText(/Öl stützt\./)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Cockpit/i });
    expect(link).toHaveAttribute("href", "/cockpit/commodities");
  });
});
