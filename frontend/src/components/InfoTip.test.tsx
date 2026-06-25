import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { InfoTip } from "./InfoTip";

describe("InfoTip", () => {
  it("zeigt einen beschrifteten Trigger + die Erklärung aus dem Glossar", () => {
    render(<InfoTip term="Top-Down" />);
    expect(screen.getByRole("button", { name: /Erklärung: Top-Down/i })).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent(/oben/i);
  });
  it("erlaubt einen expliziten Erklärtext (überschreibt das Glossar)", () => {
    render(<InfoTip term="X" text="Eigener Text" />);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Eigener Text");
  });
  it("rendert nichts, wenn keine Erklärung vorhanden ist", () => {
    const { container } = render(<InfoTip term="Unbekannt" />);
    expect(container).toBeEmptyDOMElement();
  });
});
