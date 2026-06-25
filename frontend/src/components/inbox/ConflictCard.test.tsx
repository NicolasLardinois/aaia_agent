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

// Long-Konflikt, der vom SHORT-Signal getrieben wird: GC=F long, neues Long-Urteil HOLD,
// aber neues Short-Urteil SHORT. Der Kopf muss das AUSLOESENDE SHORT zeigen — nicht das HOLD.
const gcfConflict: ConflictDTO = {
  id: "GC=F-long",
  ticker: "GC=F",
  name: "Gold",
  underlying: "precious_metal",
  wrapper: "future",
  direction: "long",
  heldVerdict: "BUY",
  newLongVerdict: "HOLD",
  newShortVerdict: "SHORT",
  confidence: 0.55,
  conflictNote: "Long gehalten, Urteil SHORT läuft gegen die Position.",
  suggestedVerdict: "REVERSE",
  suggestedRationale: "Aktives Short-Setup gegen die Long-Position — Richtung drehen erwägen.",
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
    // Das hervorgehobene SELL-Urteil steht als <span> im Kopf (font-semibold text-bear).
    // getAllByText wegen mehrfach vorkommendem "SELL" im Kartentext.
    const sellElems = screen.getAllByText("SELL");
    expect(sellElems.length).toBeGreaterThanOrEqual(1);
  });

  it("Kopf zeigt bei long-Konflikt via Short-Signal das AUSLOESENDE SHORT (nicht das HOLD)", () => {
    renderCard(gcfConflict);
    // Der Kipp-Kopf ("→ neues Urteil: …") muss das auslösende Short-Signal zeigen.
    const kopf = screen.getByText(/neues Urteil/);
    expect(kopf).toHaveTextContent("SHORT");
    expect(kopf).not.toHaveTextContent("HOLD");
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

  it("Default-Verdikt (EXIT) ist als Vorschlag markiert (genau ein aria-current)", () => {
    renderCard(xleConflict, vi.fn());
    // US29: genau EIN Verdikt ist der hervorgehobene Vorschlag (aria-current=true) und traegt EXIT.
    const markiert = document.querySelectorAll('[aria-current="true"]');
    expect(markiert).toHaveLength(1);
    expect(markiert[0]).toHaveTextContent("EXIT");
    expect(markiert[0]).toHaveTextContent(/Vorschlag/);
  });

  it("Verdikt-Optionen sind nicht-interaktive Anzeige (keine Button-Rolle)", () => {
    renderCard(xleConflict, vi.fn());
    // Die Verdikt-Chips sind reine Anzeige (kein Klick) -> keine role=button.
    // Nur die echten Protokoll-Aktionen (Gefolgt/Ignoriert/Vertagt) sind Buttons.
    expect(screen.queryByRole("button", { name: /^EXIT/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^HOLD/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^REVERSE/ })).toBeNull();
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
