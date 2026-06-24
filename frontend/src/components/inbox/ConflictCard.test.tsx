// ConflictCard.test.tsx
// TDD Rot-Phase: Tests fuer ConflictCard (US29/US30).
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ConflictCard } from "./ConflictCard";
import type { ConflictDTO } from "../../contract/inbox";

// Beispiel-Konflikt: XLE long gehalten, neues Urteil SELL -> EXIT
const xleConflict: ConflictDTO = {
  id: "XLE-long",
  ticker: "XLE",
  name: "Energy Select Sector SPDR",
  underlying: "equity_index",
  wrapper: "fund",
  direction: "long",
  heldVerdict: "BUY",
  newLongVerdict: "SELL",
  newShortVerdict: "NONE",
  confidence: 0.58,
  conflictNote: "Long gehalten, aber neues Urteil SELL — These laeuft gegen die Position.",
  suggestedVerdict: "EXIT",
  suggestedRationale: "Long-These traegt nicht mehr (SELL), aber kein bestaetigtes Short — Ausstieg erwaegen.",
  status: "offen",
};

// Short-Konflikt: TSLA short gehalten, neues Long-Urteil BUY -> REVERSE
const tslaShortConflict: ConflictDTO = {
  id: "TSLA-short",
  ticker: "TSLA",
  name: "Tesla Inc.",
  underlying: "equity",
  wrapper: "single",
  direction: "short",
  heldVerdict: "SHORT",
  newLongVerdict: "BUY",
  newShortVerdict: "COVER",
  confidence: 0.62,
  conflictNote: "Short gehalten, aber neues Urteil BUY — These laeuft gegen die Position.",
  suggestedVerdict: "REVERSE",
  suggestedRationale: "Short-These traegt nicht mehr (BUY), Richtung umkehren erwaegen.",
  status: "offen",
};

function renderCard(
  conflict: ConflictDTO = xleConflict,
  onResolve?: (id: string, decision: "gefolgt" | "ignoriert" | "vertagt") => void,
  loggedDecision?: "gefolgt" | "ignoriert" | "vertagt",
) {
  return render(
    <MemoryRouter>
      <ConflictCard conflict={conflict} onResolve={onResolve} loggedDecision={loggedDecision} />
    </MemoryRouter>,
  );
}

describe("ConflictCard (US29/US30)", () => {
  it("rendert Ticker und Kipp-Text (neues Urteil SELL im Kopf sichtbar)", () => {
    renderCard();
    expect(screen.getByText("XLE")).toBeInTheDocument();
    // Das hervorgehobene SELL-Urteil steht als <span> im Kopf (font-semibold text-red-600).
    // getAllByText wegen mehrfach vorkommendem "SELL" im Kartentext.
    const sellElems = screen.getAllByText("SELL");
    expect(sellElems.length).toBeGreaterThanOrEqual(1);
  });

  it("rendert den vollstaendigen Namen", () => {
    renderCard();
    expect(screen.getByText(/Energy Select Sector SPDR/i)).toBeInTheDocument();
  });

  it("rendert die suggestedRationale als Begruendung", () => {
    renderCard();
    expect(screen.getByText(/Long-These traegt nicht mehr/i)).toBeInTheDocument();
  });

  it("rendert die conflictNote", () => {
    renderCard();
    expect(screen.getByText(/These laeuft gegen die Position/i)).toBeInTheDocument();
  });

  it("Default-Verdikt (EXIT) ist hervorgehoben (aria-pressed=true)", () => {
    renderCard(xleConflict, vi.fn());
    // Das DEFAULT-Verdikt EXIT hat aria-pressed=true (US29: Default hervorgehoben)
    expect(screen.getByRole("button", { name: /EXIT/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("Nicht-Default-Verdikts (HOLD, REVERSE) haben aria-pressed=false", () => {
    renderCard(xleConflict, vi.fn());
    expect(screen.getByRole("button", { name: /HOLD/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /REVERSE/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("Deep-Dive-Link zeigt auf /deep-dive/XLE", () => {
    renderCard();
    const ddLink = screen.getByRole("link", { name: /Deep-Dive/i });
    expect(ddLink).toHaveAttribute("href", "/deep-dive/XLE");
  });

  it("Portfolio-Link zeigt auf /portfolio", () => {
    renderCard();
    const pLink = screen.getByRole("link", { name: /Portfolio/i });
    expect(pLink).toHaveAttribute("href", "/portfolio");
  });

  it("Aktion 'Gefolgt' ruft onResolve mit 'gefolgt' auf (US30 — keine Trade-Ausfuehrung)", async () => {
    const onResolve = vi.fn();
    renderCard(xleConflict, onResolve);
    await userEvent.click(screen.getByRole("button", { name: /Gefolgt/i }));
    expect(onResolve).toHaveBeenCalledWith("XLE-long", "gefolgt");
  });

  it("Aktion 'Ignoriert' ruft onResolve mit 'ignoriert' auf", async () => {
    const onResolve = vi.fn();
    renderCard(xleConflict, onResolve);
    await userEvent.click(screen.getByRole("button", { name: /Ignoriert/i }));
    expect(onResolve).toHaveBeenCalledWith("XLE-long", "ignoriert");
  });

  it("Aktion 'Vertagt' ruft onResolve mit 'vertagt' auf", async () => {
    const onResolve = vi.fn();
    renderCard(xleConflict, onResolve);
    await userEvent.click(screen.getByRole("button", { name: /Vertagt/i }));
    expect(onResolve).toHaveBeenCalledWith("XLE-long", "vertagt");
  });

  it("Erledigt-Modus: zeigt Audit-Label mit Entscheidung, keine Aktions-Buttons", () => {
    renderCard(xleConflict, undefined, "ignoriert");
    expect(screen.getByText(/Erledigt: ignoriert/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Gefolgt/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Ignoriert/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Vertagt/i })).toBeNull();
  });

  it("ohne onResolve werden keine Aktions-Buttons gerendert", () => {
    renderCard(xleConflict); // onResolve nicht gesetzt
    expect(screen.queryByRole("button", { name: /Gefolgt/i })).toBeNull();
  });

  it("Short-Konflikt: zeigt newShortVerdict im Kopf (COVER bei TSLA short)", () => {
    renderCard(tslaShortConflict);
    expect(screen.getByText("TSLA")).toBeInTheDocument();
    // Das hervorgehobene COVER-Urteil steht als <span> im Kopf (konsistent mit Short-Richtung).
    const coverElems = screen.getAllByText("COVER");
    expect(coverElems.length).toBeGreaterThanOrEqual(1);
  });
});
