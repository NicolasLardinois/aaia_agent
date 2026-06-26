import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarketPulse } from "./MarketPulse";
import type { Domain } from "../lib/contract";

function dom(signal: Domain["signal"], status: Domain["status"] = "available"): Domain {
  return { key: "commodities", signal, status };
}

describe("MarketPulse", () => {
  it("zeigt Titel, Tendenz und die Signal-Verteilung", () => {
    render(<MarketPulse domains={[dom("bullish"), dom("bullish"), dom("bearish"), dom("neutral")]} />);
    expect(screen.getByText("Markt-Puls")).toBeInTheDocument();
    expect(screen.getByText("Risikofreudige Tendenz")).toBeInTheDocument();
    // Verteilungs-Zeile (ein Knoten) nennt alle drei Zaehler
    expect(screen.getByText(/2 bullish/)).toBeInTheDocument();
    expect(screen.getByText(/1 bearish/)).toBeInTheDocument();
    expect(screen.getByText(/1 neutral/)).toBeInTheDocument();
    // Verteilungs-Balken ist vorhanden, wenn Signale existieren
    expect(screen.getByTestId("posture-bar")).toBeInTheDocument();
  });

  it("weist auf fehlende Daten hin, wenn keine Domaene ein Signal hat", () => {
    render(<MarketPulse domains={[dom(null, "unavailable"), dom(null, "unavailable")]} />);
    expect(screen.getByText("Keine Daten")).toBeInTheDocument();
    expect(screen.getByText(/starte oder öffne eine Analyse/i)).toBeInTheDocument();
    // Ohne Signale kein Verteilungs-Balken
    expect(screen.queryByTestId("posture-bar")).not.toBeInTheDocument();
  });

  it("nennt 'ohne Daten', wenn eine Domaene ausgefallen ist", () => {
    render(<MarketPulse domains={[dom("bullish"), dom("bearish"), dom("neutral"), dom(null, "unavailable")]} />);
    expect(screen.getByText(/1 ohne Daten/)).toBeInTheDocument();
  });
});
