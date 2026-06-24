import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CompareView } from "./CompareView";
import { demoDeepDive } from "../../data/demo/deepdive";

describe("CompareView (Gold-Future vs. physisches ETC)", () => {
  it("zeigt Roll-Yield/Hebel-Unterschied und beide Urteile", () => {
    render(<CompareView left={demoDeepDive("GC=F")} right={demoDeepDive("4GLD")} />);
    expect(screen.getByText(/-3,1/)).toBeInTheDocument();        // Future-Roll-Yield (DE-Komma)
    expect(screen.getByText(/kein Roll/i)).toBeInTheDocument();   // ETC ohne Roll
    expect(screen.getByText(/voll besichert/i)).toBeInTheDocument(); // ETC Hebel 1x
    // GC=F Konfidenz 0.47 -> HOLD; 4GLD Konfidenz 0.58 -> BUY (Wrapper-Unterschied)
    expect(screen.getByText(/^HOLD/)).toBeInTheDocument();          // GC=F Long-Urteil
    expect(screen.getByText(/^BUY/)).toBeInTheDocument();           // 4GLD Long-Urteil
  });

  it("zeigt laufende Kosten und Gegenparteirisiko je Wrapper (Konzept §5.2)", () => {
    render(<CompareView left={demoDeepDive("GC=F")} right={demoDeepDive("4GLD")} />);
    // Zeile-Label
    expect(screen.getByText("Laufende Kosten")).toBeInTheDocument();
    expect(screen.getByText("Gegenparteirisiko")).toBeInTheDocument();
    // GC=F (Future): Roll-Kosten + Börse/Clearing
    expect(screen.getByText("Roll-Kosten (Contango)")).toBeInTheDocument();
    expect(screen.getByText("Börse/Clearing")).toBeInTheDocument();
    // 4GLD (physisches ETC): TER + vollbesichert
    expect(screen.getByText("TER ~0,12 %/Jahr")).toBeInTheDocument();
    expect(screen.getByText("physisch hinterlegt")).toBeInTheDocument();
  });

  it("verschiedene underlyings (Apple vs. Gold) => Hinweis statt Vergleichstabelle", () => {
    render(<CompareView left={demoDeepDive("AAPL")} right={demoDeepDive("GC=F")} />);
    expect(screen.getByText(/nur für denselben Basiswert/i)).toBeInTheDocument();
    // Keine Vergleichszeilen, wenn der Vergleich nicht sinnvoll ist
    expect(screen.queryByText("Roll-Yield")).not.toBeInTheDocument();
    expect(screen.queryByText("Long-Urteil")).not.toBeInTheDocument();
  });
});
