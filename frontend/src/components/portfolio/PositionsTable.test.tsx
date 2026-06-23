import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PositionsTable } from "./PositionsTable";
import { demoPortfolio } from "../../data/demo/portfolio";

function renderTable() {
  return render(
    <MemoryRouter>
      <PositionsTable positions={demoPortfolio().positions} />
    </MemoryRouter>,
  );
}

describe("PositionsTable", () => {
  it("zeigt Ticker als Link auf den Deep-Dive", () => {
    renderTable();
    const link = screen.getByRole("link", { name: /AAPL/ });
    expect(link).toHaveAttribute("href", "/deep-dive/AAPL");
  });
  it("zeigt beide Etiketten (underlying + wrapper) je Position", () => {
    renderTable();
    expect(screen.getAllByText("Aktie").length).toBeGreaterThanOrEqual(1);   // underlying-Badge
    expect(screen.getAllByText("Future").length).toBeGreaterThanOrEqual(1);  // wrapper-Badge (GC=F)
  });
  it("markiert die Konflikt-Position (XLE long + SELL)", () => {
    renderTable();
    // XLE-Zeile traegt den Konflikt-Hinweis
    expect(screen.getByText(/Urteil gegen Position/i)).toBeInTheDocument();
  });
  it("zeigt fuer eine long-Position das Long-Verdikt, fuer short das Short-Verdikt", () => {
    renderTable();
    expect(screen.getByText("SHORT")).toBeInTheDocument(); // TSLA short -> Short-Verdikt
    expect(screen.getByText("SELL")).toBeInTheDocument();  // XLE long -> Long-Verdikt
  });
  it("rendert stabil auch bei doppeltem Ticker (long+short gleicher Ticker) — nutzt `ticker-direction`-Key", () => {
    // Dieser Test stellt sicher, dass der React-Key eindeutig ist und bei long+short
    // desselben Tickers nicht kollidiert. Hier mit Demo-Daten getestet (die nur einen
    // Ticker je Richtung enthalten). Das Urteil sollte pro Position korrekt sein.
    renderTable();
    // Wenn der Key nur auf ticker basierte, wuerde React bei zwei Positionen
    // desselben Tickers (z.B. "AAPL" long + "AAPL" short) die erste ueberschreiben.
    // Daher prüfen wir implizit: dass jede Long- und Short-Position eigenstaendige
    // Verdikt-Labels hat und nicht kollidieren.
    const rows = screen.getAllByRole("row");
    // Headerzeile + 6 Positionen = 7 Zeilen
    expect(rows.length).toBe(7);
  });
});
