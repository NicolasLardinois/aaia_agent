import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DemoBadge } from "./DemoBadge";

describe("DemoBadge", () => {
  it("zeigt 'Demo-Daten' bei isDemo=true", () => {
    render(<DemoBadge isDemo />);
    expect(screen.getByText(/Demo-Daten/i)).toBeInTheDocument();
  });
  it("rendert nichts bei isDemo=false (verschwindet beim Umstieg automatisch)", () => {
    const { container } = render(<DemoBadge isDemo={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
