import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DomainTile } from "./DomainTile";

const commoditiesDomain = { key: "commodities" as const, signal: "neutral" as const, status: "available" as const };
const unavailableDomain = { key: "sectors" as const, signal: null, status: "unavailable" as const };

function renderTile(domain: typeof commoditiesDomain | typeof unavailableDomain) {
  return render(
    <MemoryRouter>
      <DomainTile domain={domain} />
    </MemoryRouter>,
  );
}

describe("DomainTile", () => {
  it("Kachel Rohstoffe ist ein Link auf /cockpit/commodities", () => {
    renderTile(commoditiesDomain);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/cockpit/commodities");
  });

  it("zeigt den Kachel-Label Rohstoffe", () => {
    renderTile(commoditiesDomain);
    expect(screen.getByText("Rohstoffe")).toBeInTheDocument();
  });

  it("zeigt NEUTRAL-Badge für verfügbare Kachel", () => {
    renderTile(commoditiesDomain);
    expect(screen.getByText("NEUTRAL")).toBeInTheDocument();
  });

  it("zeigt UnavailableField für ausgefallene Kachel (sectors, signal null)", () => {
    renderTile(unavailableDomain);
    expect(screen.getByText("nicht verfügbar")).toBeInTheDocument();
  });

  it("ausgefallene Kachel ist trotzdem ein Link (auf /cockpit/sectors)", () => {
    renderTile(unavailableDomain);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/cockpit/sectors");
  });
});
