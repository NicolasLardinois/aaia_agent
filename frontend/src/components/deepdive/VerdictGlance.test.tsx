import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictGlance } from "./VerdictGlance";

describe("VerdictGlance", () => {
  it("zeigt die Eyebrow, beide Urteile und ihre Konfidenz", () => {
    render(
      <VerdictGlance
        long={{ verdict: "HOLD", confidence: 0.58 }}
        short={{ verdict: "NONE", confidence: 0.18 }}
      />,
    );
    expect(screen.getByText("Urteil auf einen Blick")).toBeInTheDocument();
    expect(screen.getByText("HOLD")).toBeInTheDocument();
    expect(screen.getByText("NONE")).toBeInTheDocument();
    expect(screen.getByText("58 %")).toBeInTheDocument();
    expect(screen.getByText("18 %")).toBeInTheDocument();
  });

  it("blendet den Konsistenz-Hinweis ein, wenn beide Linsen schwach sind (kein Edge)", () => {
    render(
      <VerdictGlance
        long={{ verdict: "HOLD", confidence: 0.58 }}
        short={{ verdict: "NONE", confidence: 0.18 }}
      />,
    );
    // HOLD + NONE sind beide "schwach" -> consistencyHint: "kein Edge"
    expect(screen.getByText(/kein Edge/i)).toBeInTheDocument();
  });

  it("faerbt ein BUY-Urteil bullish und zeigt dann keinen Schwaeche-Hinweis", () => {
    render(
      <VerdictGlance
        long={{ verdict: "BUY", confidence: 0.6 }}
        short={{ verdict: "NONE", confidence: 0.15 }}
      />,
    );
    expect(screen.getByText("BUY").className).toContain("text-bull");
    // BUY ist handlungsfaehig -> kein "kein Edge"-Hinweis
    expect(screen.queryByText(/kein Edge/i)).not.toBeInTheDocument();
  });
});
